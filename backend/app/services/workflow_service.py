"""
LiRA Backend — Workflow Service
Orchestrates workflow execution: creates runs, starts background tasks,
handles per-node approval (continue/improve/retry), and manages state persistence.
"""

import asyncio
import json
import os
import sys
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.approval import Approval
from app.models.artifact import Artifact
from app.models.node_execution import NodeExecution
from app.models.node_review_action import NodeReviewAction
from app.models.research_history import ResearchHistory
from app.models.research_message import ResearchMessage
from app.models.workflow_run import WorkflowRun
from app.services.event_service import EventService
from app.workflow.runner import WorkflowRunner, GraphInterruptException, NodeApprovalInterrupt

# Thread pool for background workflow execution
_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="lira-workflow")

# Track node order globally per run
_node_counters: Dict[str, int] = {}


class WorkflowService:
    """Service layer for workflow orchestration."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def start_workflow(
        self,
        research: ResearchHistory,
    ) -> WorkflowRun:
        """Create a workflow run and start it in the background."""
        settings = get_settings()

        # Determine run number
        result = await self.db.execute(
            select(WorkflowRun)
            .where(WorkflowRun.research_id == research.id)
            .order_by(desc(WorkflowRun.run_number))
            .limit(1)
        )
        last_run = result.scalar_one_or_none()
        run_number = (last_run.run_number + 1) if last_run else 1

        # Create work directory
        work_dir = str(
            Path(settings.STORAGE_LOCAL_ROOT) / str(research.id) / f"run-{run_number}"
        )
        Path(work_dir).mkdir(parents=True, exist_ok=True)

        # Create workflow run record
        run = WorkflowRun(
            research_id=research.id,
            run_number=run_number,
            status="running",
            thread_id=f"research-{research.id}-run-{run_number}",
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(run)

        # Update research status
        research.status = "running"
        research.started_at = research.started_at or datetime.now(timezone.utc)

        # Add system message
        msg = ResearchMessage(
            research_id=research.id,
            role="system",
            content=f"Starting pipeline (Run #{run_number})...",
            message_type="node_event",
            metadata_extra={"run_number": run_number},
        )
        self.db.add(msg)

        await self.db.commit()
        await self.db.refresh(run)

        # Parse databases
        db_list = _parse_databases(research.databases)

        # Get main event loop
        loop = asyncio.get_running_loop()

        # Initialize node counter
        _node_counters[str(run.id)] = 0

        # Submit to thread pool
        _executor.submit(
            _run_workflow_sync,
            loop,
            str(research.id),
            str(run.id),
            work_dir,
            research.topic,
            research.timeframe,
            db_list,
        )

        return run

    async def resume_with_action(
        self,
        research: ResearchHistory,
        node_execution_id: str,
        action: str,
        feedback: Optional[str] = None,
    ) -> None:
        """
        Resume a paused workflow after user action on a node.
        action: "continue" | "improve_result" | "retry"
        """
        settings = get_settings()

        # Find the paused run
        result = await self.db.execute(
            select(WorkflowRun)
            .where(
                WorkflowRun.research_id == research.id,
                WorkflowRun.status == "paused",
            )
            .order_by(desc(WorkflowRun.run_number))
            .limit(1)
        )
        run = result.scalar_one_or_none()
        if not run:
            raise ValueError("No paused run found to resume")

        work_dir = str(
            Path(settings.STORAGE_LOCAL_ROOT) / str(research.id) / f"run-{run.run_number}"
        )

        # Record the review action
        review_action = NodeReviewAction(
            node_execution_id=uuid.UUID(node_execution_id),
            research_id=research.id,
            action_type=action,
            feedback_text=feedback,
        )
        self.db.add(review_action)

        # Update node execution status
        result = await self.db.execute(
            select(NodeExecution).where(NodeExecution.id == uuid.UUID(node_execution_id))
        )
        node_exec = result.scalar_one_or_none()

        if node_exec:
            if action == "continue":
                node_exec.status = "approved"
                node_exec.approved_at = datetime.now(timezone.utc)
            elif action == "improve_result":
                node_exec.status = "revising"
                node_exec.revision_number = (node_exec.revision_number or 0) + 1
                node_exec.feedback_text = feedback
            elif action == "retry":
                node_exec.status = "running"
                node_exec.attempt_number = (node_exec.attempt_number or 1) + 1

        # Update statuses
        run.status = "running"
        research.status = "running"

        # Add timeline message
        action_label = {
            "continue": "✓ User approved — continuing to next step",
            "improve_result": f"🔄 User requested revision: {feedback or ''}",
            "retry": "🔁 User retrying failed step",
        }.get(action, f"User action: {action}")

        msg = ResearchMessage(
            research_id=research.id,
            role="user",
            content=action_label,
            message_type="node_event",
            metadata_extra={
                "action": action,
                "node_execution_id": node_execution_id,
                "feedback": feedback,
            },
        )
        self.db.add(msg)

        await self.db.commit()

        # Build resume value for the graph
        resume_value = {"action": action}
        if action == "improve_result" and feedback:
            resume_value["feedback"] = feedback

        # Parse databases
        db_list = _parse_databases(research.databases)

        # Get main event loop
        loop = asyncio.get_running_loop()

        # Submit resume to thread pool
        _executor.submit(
            _resume_workflow_sync,
            loop,
            str(research.id),
            str(run.id),
            work_dir,
            research.topic,
            research.timeframe,
            db_list,
            resume_value,
        )

    async def resume_workflow(
        self,
        research: ResearchHistory,
        approval: Approval,
        resume_value: Any,
    ) -> None:
        """Legacy resume: for ASReview file upload flow."""
        settings = get_settings()

        result = await self.db.execute(
            select(WorkflowRun)
            .where(
                WorkflowRun.research_id == research.id,
                WorkflowRun.status == "paused",
            )
            .order_by(desc(WorkflowRun.run_number))
            .limit(1)
        )
        run = result.scalar_one_or_none()
        if not run:
            raise ValueError("No paused run found to resume")

        work_dir = str(
            Path(settings.STORAGE_LOCAL_ROOT) / str(research.id) / f"run-{run.run_number}"
        )

        run.status = "running"
        research.status = "running"

        msg = ResearchMessage(
            research_id=research.id,
            role="system",
            content="Pipeline resuming after file upload...",
            message_type="node_event",
        )
        self.db.add(msg)

        await self.db.commit()

        db_list = _parse_databases(research.databases)
        loop = asyncio.get_running_loop()

        _executor.submit(
            _resume_workflow_sync,
            loop,
            str(research.id),
            str(run.id),
            work_dir,
            research.topic,
            research.timeframe,
            db_list,
            resume_value,
        )


def _parse_databases(databases) -> List[str]:
    """Parse databases from various formats."""
    if isinstance(databases, list):
        return databases
    elif isinstance(databases, dict):
        return list(databases.values()) if databases else []
    return ["Google Scholar", "arXiv", "OpenAlex", "PubMed", "CrossRef"]


@contextmanager
def _safe_io_context(work_dir: str):
    """
    Redirect stdout/stderr to a log file during pipeline execution.
    This prevents 'I/O operation on closed file' crashes when uvicorn
    hot-reloads while a background thread is running agent code with print().
    """
    log_path = os.path.join(work_dir, "pipeline_output.log")
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    try:
        log_file = open(log_path, "a", encoding="utf-8", buffering=1)
        sys.stdout = log_file
        sys.stderr = log_file
        yield
    except ValueError:
        # stdout/stderr already closed — ignore
        yield
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        try:
            log_file.close()
        except Exception:
            pass


def _run_workflow_sync(
    loop: asyncio.AbstractEventLoop,
    research_id: str,
    run_id: str,
    work_dir: str,
    topic: str,
    timeframe: str,
    databases: List[str],
) -> None:
    """Synchronous workflow execution (runs in thread pool)."""
    def notify_node_completed(**kwargs):
        asyncio.run_coroutine_threadsafe(
            _persist_node_completed(research_id=research_id, run_id=run_id, **kwargs), loop
        )

    def notify_node_approval(**kwargs):
        asyncio.run_coroutine_threadsafe(
            _persist_node_approval(research_id=research_id, run_id=run_id, **kwargs), loop
        )

    runner = WorkflowRunner(
        research_id=research_id,
        run_id=run_id,
        work_dir=work_dir,
        topic=topic,
        timeframe=timeframe,
        databases=databases,
        db_callbacks={
            "node_completed": notify_node_completed,
            "node_approval_required": notify_node_approval,
        },
    )

    with _safe_io_context(work_dir):
        try:
            final_state = runner.execute()

            asyncio.run_coroutine_threadsafe(_persist_completion(
                research_id=research_id,
                run_id=run_id,
                final_state=final_state,
                work_dir=work_dir,
            ), loop)

        except NodeApprovalInterrupt:
            # Per-node approval — persist and wait for user action
            pass

        except GraphInterruptException as e:
            # Legacy ASReview interrupt
            asyncio.run_coroutine_threadsafe(_persist_interrupt(
                research_id=research_id,
                run_id=run_id,
                interrupt_data=e.interrupt_data,
            ), loop)

        except Exception as e:
            error_msg = str(e)
            error_tb = traceback.format_exc()
            print(f"[WorkflowRunner] FAILED: {error_msg}")
            print(error_tb)

            asyncio.run_coroutine_threadsafe(_persist_failure(
                research_id=research_id,
                run_id=run_id,
                error_msg=error_msg,
                error_tb=error_tb,
            ), loop)


def _resume_workflow_sync(
    loop: asyncio.AbstractEventLoop,
    research_id: str,
    run_id: str,
    work_dir: str,
    topic: str,
    timeframe: str,
    databases: List[str],
    resume_value: Any,
) -> None:
    """Synchronous resume execution (runs in thread pool)."""
    def notify_node_completed(**kwargs):
        asyncio.run_coroutine_threadsafe(
            _persist_node_completed(research_id=research_id, run_id=run_id, **kwargs), loop
        )

    def notify_node_approval(**kwargs):
        asyncio.run_coroutine_threadsafe(
            _persist_node_approval(research_id=research_id, run_id=run_id, **kwargs), loop
        )

    runner = WorkflowRunner(
        research_id=research_id,
        run_id=run_id,
        work_dir=work_dir,
        topic=topic,
        timeframe=timeframe,
        databases=databases,
        db_callbacks={
            "node_completed": notify_node_completed,
            "node_approval_required": notify_node_approval,
        },
    )

    with _safe_io_context(work_dir):
        try:
            final_state = runner.resume(resume_value)

            asyncio.run_coroutine_threadsafe(_persist_completion(
                research_id=research_id,
                run_id=run_id,
                final_state=final_state,
                work_dir=work_dir,
            ), loop)

        except NodeApprovalInterrupt:
            pass

        except GraphInterruptException as e:
            asyncio.run_coroutine_threadsafe(_persist_interrupt(
                research_id=research_id,
                run_id=run_id,
                interrupt_data=e.interrupt_data,
            ), loop)

        except Exception as e:
            error_msg = str(e)
            error_tb = traceback.format_exc()
            print(f"[WorkflowRunner] Resume FAILED: {error_msg}")
            print(error_tb)

            asyncio.run_coroutine_threadsafe(_persist_failure(
                research_id=research_id,
                run_id=run_id,
                error_msg=error_msg,
                error_tb=error_tb,
            ), loop)


# ── Database persistence helpers ───────────────────────────


async def _persist_node_approval(
    research_id: str,
    run_id: str,
    node_name: str,
    step_label: str = "",
    description: str = "",
    approval_id: str | None = None,
    node_execution_id: str | None = None,
) -> None:
    """Persist per-node approval pause to database."""
    from app.workflow.runner import _serialize_state_snapshot
    try:
        approval_uuid = uuid.UUID(approval_id) if approval_id else uuid.uuid4()
        node_execution_uuid = uuid.UUID(node_execution_id) if node_execution_id else uuid.uuid4()

        async with AsyncSessionLocal() as db:
            # Create node execution record with waiting_for_approval status
            node_exec = NodeExecution(
                id=node_execution_uuid,
                run_id=uuid.UUID(run_id),
                node_name=node_name,
                step_label=step_label,
                status="waiting_for_approval",
                node_order=_node_counters.get(run_id, 0),
            )
            db.add(node_exec)
            await db.flush()  # Get the ID

            # Update workflow run
            result = await db.execute(
                select(WorkflowRun).where(WorkflowRun.id == uuid.UUID(run_id))
            )
            run = result.scalar_one_or_none()
            if run:
                run.status = "paused"
                run.current_node = node_name
                run.current_node_execution_id = node_exec.id

            # Update research
            result = await db.execute(
                select(ResearchHistory).where(ResearchHistory.id == uuid.UUID(research_id))
            )
            research = result.scalar_one_or_none()
            if research:
                research.status = "paused"
                research.current_step = step_label or node_name
                research.latest_summary = f"Waiting for approval: {description}"

            # Create generic approval record
            approval = Approval(
                id=approval_uuid,
                run_id=uuid.UUID(run_id),
                research_id=uuid.UUID(research_id),
                node_name=node_name,
                approval_type="node_approval",
                status="pending",
                request_data={
                    "node_name": node_name,
                    "step_label": step_label,
                    "description": description,
                    "node_execution_id": str(node_exec.id),
                },
            )
            db.add(approval)

            # Add timeline message
            msg = ResearchMessage(
                research_id=uuid.UUID(research_id),
                role="system",
                content=f"⏸ [{step_label}] {description} — waiting for your approval",
                message_type="approval",
                metadata_extra={
                    "node_name": node_name,
                    "step_label": step_label,
                    "description": description,
                    "node_execution_id": str(node_exec.id),
                    "approval_type": "node_approval",
                },
            )
            db.add(msg)

            await db.commit()

        EventService(research_id=research_id, run_id=run_id).node_waiting_for_approval(
            node_name=node_name,
            step_label=step_label,
            description=description,
            approval_id=str(approval_uuid),
            node_execution_id=str(node_execution_uuid),
            approval_type="node_approval",
        )
    except Exception as e:
        print(f"[ERROR] Failed to persist node approval for {node_name}: {e}")
        traceback.print_exc()


async def _persist_node_completed(
    research_id: str,
    run_id: str,
    node_name: str,
    step_label: str,
    output_summary: Dict[str, Any],
    logs: List[str],
    duration_ms: int,
) -> None:
    """Persist intermediate node completion."""
    from app.workflow.runner import _serialize_state_snapshot
    try:
        safe_output = _serialize_state_snapshot(output_summary) if output_summary else {}

        # Increment node counter
        _node_counters[run_id] = _node_counters.get(run_id, 0) + 1

        async with AsyncSessionLocal() as db:
            node_exec = NodeExecution(
                run_id=uuid.UUID(run_id),
                node_name=node_name,
                step_label=step_label,
                status="completed",
                duration_ms=duration_ms,
                output_summary=safe_output,
                logs={"logs": logs},
                node_order=_node_counters.get(run_id, 0),
                completed_at=datetime.now(timezone.utc),
            )
            db.add(node_exec)

            # Update research status
            result = await db.execute(
                select(ResearchHistory).where(ResearchHistory.id == uuid.UUID(research_id))
            )
            research = result.scalar_one_or_none()
            if research:
                research.current_step = step_label or node_name
                research.latest_summary = f"Completed {node_name}"

            # Timeline message
            msg_content = f"Completed {node_name}"
            if step_label:
                msg_content = f"[{step_label}] {msg_content}"

            msg = ResearchMessage(
                research_id=uuid.UUID(research_id),
                role="system",
                content=msg_content,
                message_type="node_event",
                metadata_extra={"duration_ms": duration_ms, "output": safe_output},
            )
            db.add(msg)

            await db.commit()
    except Exception as e:
        print(f"[ERROR] Failed to persist node {node_name}: {e}")


async def _persist_completion(
    research_id: str,
    run_id: str,
    final_state: Dict[str, Any],
    work_dir: str,
) -> None:
    """Persist successful pipeline completion."""
    from app.workflow.runner import _serialize_state_snapshot
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(WorkflowRun).where(WorkflowRun.id == uuid.UUID(run_id))
        )
        run = result.scalar_one_or_none()
        if run:
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
            run.current_node = None
            run.state_snapshot = _serialize_state_snapshot(final_state)

        result = await db.execute(
            select(ResearchHistory).where(ResearchHistory.id == uuid.UUID(research_id))
        )
        research = result.scalar_one_or_none()
        if research:
            research.status = "completed"
            research.completed_at = datetime.now(timezone.utc)
            research.current_step = final_state.get("current_step", "Completed")
            research.latest_summary = "Pipeline completed successfully"
            research.latest_error = None

        msg = ResearchMessage(
            research_id=uuid.UUID(research_id),
            role="system",
            content="✓ Pipeline completed successfully!",
            message_type="workflow_completed",
        )
        db.add(msg)

        await _register_artifacts(db, research_id, run_id, work_dir)
        await db.commit()


async def _persist_interrupt(
    research_id: str,
    run_id: str,
    interrupt_data: Any,
) -> None:
    """Persist legacy interrupt (ASReview file upload)."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(WorkflowRun).where(WorkflowRun.id == uuid.UUID(run_id))
        )
        run = result.scalar_one_or_none()
        if run:
            run.status = "paused"

        result = await db.execute(
            select(ResearchHistory).where(ResearchHistory.id == uuid.UUID(research_id))
        )
        research = result.scalar_one_or_none()
        if research:
            research.status = "paused"
            research.current_step = "Step 3.c — ASReview Screening"
            research.latest_summary = "Waiting for human screening"

        request_data = interrupt_data if isinstance(interrupt_data, dict) else {"message": str(interrupt_data)}
        approval = Approval(
            run_id=uuid.UUID(run_id),
            research_id=uuid.UUID(research_id),
            node_name="asreview_screen",
            approval_type="asreview_screening",
            status="pending",
            request_data=request_data,
        )
        db.add(approval)

        msg = ResearchMessage(
            research_id=uuid.UUID(research_id),
            role="system",
            content="⏸ Pipeline paused — ASReview manual screening required.",
            message_type="approval",
            metadata_extra=request_data,
        )
        db.add(msg)

        await db.commit()


async def _persist_failure(
    research_id: str,
    run_id: str,
    error_msg: str,
    error_tb: str,
) -> None:
    """Persist pipeline failure."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(WorkflowRun).where(WorkflowRun.id == uuid.UUID(run_id))
        )
        run = result.scalar_one_or_none()
        if run:
            run.status = "failed"
            run.completed_at = datetime.now(timezone.utc)
            run.error_message = error_msg
            run.error_traceback = error_tb

        result = await db.execute(
            select(ResearchHistory).where(ResearchHistory.id == uuid.UUID(research_id))
        )
        research = result.scalar_one_or_none()
        if research:
            research.status = "failed"
            research.latest_error = error_msg

        msg = ResearchMessage(
            research_id=uuid.UUID(research_id),
            role="system",
            content=f"✗ Pipeline failed: {error_msg}",
            message_type="error",
            metadata_extra={"error": error_msg},
        )
        db.add(msg)

        await db.commit()


async def _register_artifacts(
    db: AsyncSession,
    research_id: str,
    run_id: str,
    work_dir: str,
) -> None:
    """Register all files in work_dir as artifacts."""
    from app.workflow.runner import _get_file_type, _get_mime_type

    work_path = Path(work_dir)
    if not work_path.exists():
        return

    for f in work_path.rglob("*"):
        if not f.is_file():
            continue
        if f.name.startswith(".") or f.stat().st_size == 0:
            continue

        artifact = Artifact(
            research_id=uuid.UUID(research_id),
            run_id=uuid.UUID(run_id),
            filename=f.name,
            file_type=_get_file_type(f.name),
            mime_type=_get_mime_type(f.name),
            file_size=f.stat().st_size,
            storage_path=str(f),
            description="Generated by pipeline",
        )
        db.add(artifact)
