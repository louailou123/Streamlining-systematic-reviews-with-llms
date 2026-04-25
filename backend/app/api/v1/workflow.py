"""
LiRA Backend — Workflow API Routes
Start, resume, cancel workflows. List runs and node executions.
Per-node approval: continue, improve, retry.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.exceptions import NotFoundError, LiRAException
from app.db.session import get_db
from app.models.approval import Approval
from app.models.node_execution import NodeExecution
from app.models.research_history import ResearchHistory
from app.models.user import User
from app.models.workflow_run import WorkflowRun
from app.schemas.workflow import (
    NodeApprovalAction,
    NodeExecutionResponse,
    PendingApprovalResponse,
    WorkflowRunResponse,
    WorkflowStateResponse,
)

router = APIRouter(prefix="/workflow", tags=["Workflow"])


async def _get_research_for_user(
    research_id: UUID, user: User, db: AsyncSession
) -> ResearchHistory:
    result = await db.execute(
        select(ResearchHistory).where(
            ResearchHistory.id == research_id,
            ResearchHistory.user_id == user.id,
        )
    )
    research = result.scalar_one_or_none()
    if not research:
        raise NotFoundError("Research")
    return research


@router.post("/{research_id}/start", response_model=WorkflowRunResponse)
async def start_workflow(
    research_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start (or restart) the LiRA pipeline for a research project."""
    research = await _get_research_for_user(research_id, current_user, db)

    from app.services.workflow_service import WorkflowService
    workflow_service = WorkflowService(db)
    run = await workflow_service.start_workflow(research)
    return run


@router.post("/{research_id}/cancel")
async def cancel_workflow(
    research_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a running workflow."""
    research = await _get_research_for_user(research_id, current_user, db)

    result = await db.execute(
        select(WorkflowRun)
        .where(
            WorkflowRun.research_id == research_id,
            WorkflowRun.status.in_(["pending", "running", "paused"]),
        )
        .order_by(desc(WorkflowRun.run_number))
        .limit(1)
    )
    run = result.scalar_one_or_none()

    if not run:
        raise NotFoundError("No active workflow run found")

    run.status = "cancelled"
    research.status = "failed"
    research.latest_error = "Cancelled by user"
    await db.commit()

    return {"status": "cancelled", "run_id": str(run.id)}


# ── Per-Node Approval Endpoints ─────────────────────────────


@router.get("/{research_id}/pending-approval", response_model=PendingApprovalResponse)
async def get_pending_approval(
    research_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current pending approval for a research pipeline."""
    _ = await _get_research_for_user(research_id, current_user, db)

    result = await db.execute(
        select(Approval)
        .where(
            Approval.research_id == research_id,
            Approval.status == "pending",
        )
        .order_by(desc(Approval.requested_at))
        .limit(1)
    )
    approval = result.scalar_one_or_none()

    if not approval:
        return PendingApprovalResponse(has_pending=False)

    req = approval.request_data or {}

    # Get output_summary from the node execution
    output_summary = None
    ne_id = req.get("node_execution_id")
    if ne_id:
        ne_result = await db.execute(
            select(NodeExecution).where(NodeExecution.id == ne_id)
        )
        ne = ne_result.scalar_one_or_none()
        if ne and ne.output_summary:
            output_summary = ne.output_summary

    return PendingApprovalResponse(
        has_pending=True,
        approval_id=str(approval.id),
        node_execution_id=req.get("node_execution_id"),
        node_name=approval.node_name,
        step_label=req.get("step_label"),
        description=req.get("description"),
        approval_type=approval.approval_type,
        output_summary=output_summary,
        download_file=req.get("download_file"),
        download_description=req.get("download_description"),
        asreview_url=req.get("asreview_url"),
        upload_description=req.get("upload_description"),
    )


@router.post("/{research_id}/nodes/{node_execution_id}/action")
async def node_approval_action(
    research_id: UUID,
    node_execution_id: UUID,
    body: NodeApprovalAction,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    User action on a node approval gate.
    Actions: continue, improve_result, retry
    """
    research = await _get_research_for_user(research_id, current_user, db)

    # Verify the node execution exists and belongs to this research
    result = await db.execute(
        select(NodeExecution)
        .join(WorkflowRun)
        .where(
            NodeExecution.id == node_execution_id,
            WorkflowRun.research_id == research_id,
        )
    )
    node_exec = result.scalar_one_or_none()
    if not node_exec:
        raise NotFoundError("Node execution")

    if node_exec.status not in ("waiting_for_approval", "failed"):
        raise LiRAException(
            f"Node is not awaiting action (current status: {node_exec.status})",
            status_code=400,
        )

    # Mark the pending approval as responded
    approval_result = await db.execute(
        select(Approval)
        .where(
            Approval.research_id == research_id,
            Approval.status == "pending",
            Approval.node_name == node_exec.node_name,
        )
        .order_by(desc(Approval.requested_at))
        .limit(1)
    )
    approval = approval_result.scalar_one_or_none()
    if approval:
        from datetime import datetime, timezone
        approval.status = "approved" if body.action == "continue" else "responded"
        approval.responded_at = datetime.now(timezone.utc)
        approval.response_data = {
            "action": body.action,
            "feedback": body.feedback,
        }

    # Resume the workflow via service
    from app.services.workflow_service import WorkflowService
    workflow_service = WorkflowService(db)
    await workflow_service.resume_with_action(
        research=research,
        node_execution_id=str(node_execution_id),
        action=body.action,
        feedback=body.feedback,
    )

    return {
        "status": "resumed",
        "action": body.action,
        "node_name": node_exec.node_name,
    }


@router.post("/{research_id}/retry")
async def retry_failed_pipeline(
    research_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retry a failed pipeline from the last checkpoint.
    No node_execution_id required — just resumes the failed run.
    """
    research = await _get_research_for_user(research_id, current_user, db)

    if research.status != "failed":
        raise LiRAException(
            f"Research is not in failed state (current: {research.status})",
            status_code=400,
        )

    from app.services.workflow_service import WorkflowService
    workflow_service = WorkflowService(db)
    await workflow_service.retry_failed_run(research=research)

    return {
        "status": "retrying",
        "research_id": str(research_id),
    }


@router.post("/{research_id}/nodes/{node_execution_id}/upload")
async def upload_asreview_file(
    research_id: UUID,
    node_execution_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload ASReview export file and resume the pipeline.
    Saves the file to the work directory and resumes with the uploaded file path.
    """
    import shutil
    from pathlib import Path
    from app.core.config import get_settings
    from datetime import datetime, timezone

    research = await _get_research_for_user(research_id, current_user, db)

    # Verify node execution
    result = await db.execute(
        select(NodeExecution)
        .join(WorkflowRun)
        .where(
            NodeExecution.id == node_execution_id,
            WorkflowRun.research_id == research_id,
        )
    )
    node_exec = result.scalar_one_or_none()
    if not node_exec:
        raise NotFoundError("Node execution")

    if node_exec.status != "waiting_for_approval":
        raise LiRAException(
            f"Node is not awaiting file upload (current status: {node_exec.status})",
            status_code=400,
        )

    # Save uploaded file to the work directory
    settings = get_settings()
    run_result = await db.execute(
        select(WorkflowRun)
        .where(
            WorkflowRun.research_id == research_id,
            WorkflowRun.status == "paused",
        )
        .order_by(desc(WorkflowRun.run_number))
        .limit(1)
    )
    run = run_result.scalar_one_or_none()
    if not run:
        raise LiRAException("No paused run found", status_code=400)

    work_dir = Path(settings.STORAGE_LOCAL_ROOT) / str(research_id) / f"run-{run.run_number}"
    work_dir.mkdir(parents=True, exist_ok=True)

    file_path = work_dir / (file.filename or "asreview_export.csv")
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Mark the approval as responded
    approval_result = await db.execute(
        select(Approval)
        .where(
            Approval.research_id == research_id,
            Approval.status == "pending",
            Approval.node_name == node_exec.node_name,
        )
        .order_by(desc(Approval.requested_at))
        .limit(1)
    )
    approval = approval_result.scalar_one_or_none()
    if approval:
        approval.status = "approved"
        approval.responded_at = datetime.now(timezone.utc)
        approval.response_data = {
            "action": "continue",
            "uploaded_file": str(file_path),
        }

    # Resume the workflow with the uploaded file path
    from app.services.workflow_service import WorkflowService
    workflow_service = WorkflowService(db)
    await workflow_service.resume_with_action(
        research=research,
        node_execution_id=str(node_execution_id),
        action="continue",
        feedback=None,
    )

    return {
        "status": "uploaded_and_resumed",
        "filename": file.filename,
        "file_path": str(file_path),
    }


# ── Existing Query Endpoints ────────────────────────────────


@router.get("/{research_id}/runs", response_model=list[WorkflowRunResponse])
async def list_runs(
    research_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all workflow runs for a research project."""
    _ = await _get_research_for_user(research_id, current_user, db)

    result = await db.execute(
        select(WorkflowRun)
        .where(WorkflowRun.research_id == research_id)
        .order_by(desc(WorkflowRun.run_number))
    )
    runs = result.scalars().all()
    return [WorkflowRunResponse.model_validate(r) for r in runs]


@router.get("/{research_id}/nodes", response_model=list[NodeExecutionResponse])
async def list_node_executions(
    research_id: UUID,
    run_id: UUID = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List node executions. Filter by run_id if provided."""
    _ = await _get_research_for_user(research_id, current_user, db)

    query = (
        select(NodeExecution)
        .join(WorkflowRun)
        .where(WorkflowRun.research_id == research_id)
    )

    if run_id:
        query = query.where(NodeExecution.run_id == run_id)

    query = query.order_by(NodeExecution.started_at)

    result = await db.execute(query)
    nodes = result.scalars().all()
    return [NodeExecutionResponse.model_validate(n) for n in nodes]


@router.get("/{research_id}/state", response_model=WorkflowStateResponse)
async def get_workflow_state(
    research_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current workflow state snapshot."""
    research = await _get_research_for_user(research_id, current_user, db)

    result = await db.execute(
        select(WorkflowRun)
        .where(WorkflowRun.research_id == research_id)
        .order_by(desc(WorkflowRun.run_number))
        .limit(1)
    )
    latest_run = result.scalar_one_or_none()

    return WorkflowStateResponse(
        research_id=research_id,
        status=research.status,
        current_step=research.current_step,
        current_node=latest_run.current_node if latest_run else None,
        state_snapshot=latest_run.state_snapshot if latest_run else None,
    )
