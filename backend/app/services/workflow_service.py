"""
LiRA Backend — Workflow Service
Orchestrates workflow execution: creates runs, starts background tasks,
handles approvals, and manages state persistence.
"""

import asyncio
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
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
from app.models.research_history import ResearchHistory
from app.models.research_message import ResearchMessage
from app.models.workflow_run import WorkflowRun
from app.workflow.runner import WorkflowRunner, GraphInterruptException

# Thread pool for background workflow execution
_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="lira-workflow")


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
        databases = research.databases
        if isinstance(databases, list):
            db_list = databases
        elif isinstance(databases, dict):
            db_list = list(databases.values()) if databases else []
        else:
            db_list = ["Google Scholar", "arXiv", "OpenAlex", "PubMed", "CrossRef"]

        # Submit to thread pool
        _executor.submit(
            _run_workflow_sync,
            research_id=str(research.id),
            run_id=str(run.id),
            work_dir=work_dir,
            topic=research.topic,
            timeframe=research.timeframe,
            databases=db_list,
        )

        return run

    async def resume_workflow(
        self,
        research: ResearchHistory,
        approval: Approval,
        resume_value: Any,
    ) -> None:
        """Resume a paused workflow after human-in-the-loop action."""
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

        # Update statuses
        run.status = "running"
        research.status = "running"

        msg = ResearchMessage(
            research_id=research.id,
            role="system",
            content="Pipeline resuming after approval...",
            message_type="node_event",
        )
        self.db.add(msg)

        await self.db.commit()

        # Parse databases
        databases = research.databases
        if isinstance(databases, list):
            db_list = databases
        elif isinstance(databases, dict):
            db_list = list(databases.values()) if databases else []
        else:
            db_list = ["Google Scholar", "arXiv", "OpenAlex", "PubMed", "CrossRef"]

        # Submit resume to thread pool
        _executor.submit(
            _resume_workflow_sync,
            research_id=str(research.id),
            run_id=str(run.id),
            work_dir=work_dir,
            topic=research.topic,
            timeframe=research.timeframe,
            databases=db_list,
            resume_value=resume_value,
        )


def _run_workflow_sync(
    research_id: str,
    run_id: str,
    work_dir: str,
    topic: str,
    timeframe: str,
    databases: List[str],
) -> None:
    """
    Synchronous workflow execution (runs in thread pool).
    Persists results to DB via sync callbacks.
    """
    runner = WorkflowRunner(
        research_id=research_id,
        run_id=run_id,
        work_dir=work_dir,
        topic=topic,
        timeframe=timeframe,
        databases=databases,
    )

    try:
        final_state = runner.execute()

        # Persist final state to database
        asyncio.run(_persist_completion(
            research_id=research_id,
            run_id=run_id,
            final_state=final_state,
            work_dir=work_dir,
        ))

    except GraphInterruptException as e:
        # Pipeline paused for human-in-the-loop
        asyncio.run(_persist_interrupt(
            research_id=research_id,
            run_id=run_id,
            interrupt_data=e.interrupt_data,
        ))

    except Exception as e:
        error_msg = str(e)
        error_tb = traceback.format_exc()
        print(f"[WorkflowRunner] FAILED: {error_msg}")
        print(error_tb)

        asyncio.run(_persist_failure(
            research_id=research_id,
            run_id=run_id,
            error_msg=error_msg,
            error_tb=error_tb,
        ))


def _resume_workflow_sync(
    research_id: str,
    run_id: str,
    work_dir: str,
    topic: str,
    timeframe: str,
    databases: List[str],
    resume_value: Any,
) -> None:
    """Synchronous resume execution (runs in thread pool)."""
    runner = WorkflowRunner(
        research_id=research_id,
        run_id=run_id,
        work_dir=work_dir,
        topic=topic,
        timeframe=timeframe,
        databases=databases,
    )

    try:
        final_state = runner.resume(resume_value)

        asyncio.run(_persist_completion(
            research_id=research_id,
            run_id=run_id,
            final_state=final_state,
            work_dir=work_dir,
        ))

    except GraphInterruptException as e:
        asyncio.run(_persist_interrupt(
            research_id=research_id,
            run_id=run_id,
            interrupt_data=e.interrupt_data,
        ))

    except Exception as e:
        error_msg = str(e)
        error_tb = traceback.format_exc()
        asyncio.run(_persist_failure(
            research_id=research_id,
            run_id=run_id,
            error_msg=error_msg,
            error_tb=error_tb,
        ))


# ── Database persistence helpers (called from background threads) ──

async def _persist_completion(
    research_id: str,
    run_id: str,
    final_state: Dict[str, Any],
    work_dir: str,
) -> None:
    """Persist successful completion to database."""
    async with AsyncSessionLocal() as db:
        # Update workflow run
        result = await db.execute(
            select(WorkflowRun).where(WorkflowRun.id == uuid.UUID(run_id))
        )
        run = result.scalar_one_or_none()
        if run:
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
            # Serialize state snapshot (exclude non-serializable fields)
            from app.workflow.runner import _serialize_state_snapshot
            run.state_snapshot = _serialize_state_snapshot(final_state)

        # Update research history
        result = await db.execute(
            select(ResearchHistory).where(ResearchHistory.id == uuid.UUID(research_id))
        )
        research = result.scalar_one_or_none()
        if research:
            research.status = "completed"
            research.completed_at = datetime.now(timezone.utc)
            research.current_step = final_state.get("current_step", "Completed")
            research.latest_summary = f"Pipeline completed successfully"
            research.latest_error = None

        # Add completion message
        msg = ResearchMessage(
            research_id=uuid.UUID(research_id),
            role="system",
            content="✓ Pipeline completed successfully!",
            message_type="workflow_completed",
        )
        db.add(msg)

        # Register artifacts from work directory
        await _register_artifacts(db, research_id, run_id, work_dir)

        await db.commit()


async def _persist_interrupt(
    research_id: str,
    run_id: str,
    interrupt_data: Any,
) -> None:
    """Persist interrupt (human-in-the-loop) to database."""
    async with AsyncSessionLocal() as db:
        # Update workflow run
        result = await db.execute(
            select(WorkflowRun).where(WorkflowRun.id == uuid.UUID(run_id))
        )
        run = result.scalar_one_or_none()
        if run:
            run.status = "paused"

        # Update research
        result = await db.execute(
            select(ResearchHistory).where(ResearchHistory.id == uuid.UUID(research_id))
        )
        research = result.scalar_one_or_none()
        if research:
            research.status = "paused"
            research.current_step = "Step 3.c — ASReview Screening"
            research.latest_summary = "Waiting for human screening"

        # Create approval record
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

        # Add message
        msg = ResearchMessage(
            research_id=uuid.UUID(research_id),
            role="system",
            content="⏸ Pipeline paused — ASReview manual screening required. Download the import CSV, screen papers in ASReview, then upload the export CSV to resume.",
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
    """Persist failure to database."""
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
    """Register all files in work_dir as artifacts in the database."""
    from app.workflow.runner import _get_file_type, _get_mime_type

    work_path = Path(work_dir)
    if not work_path.exists():
        return

    for f in work_path.rglob("*"):
        if not f.is_file():
            continue
        # Skip very small or hidden files
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
            description=f"Generated by pipeline",
        )
        db.add(artifact)
