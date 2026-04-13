"""
LiRA Backend — Workflow API Routes
Start, resume, cancel workflows. List runs and node executions.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.node_execution import NodeExecution
from app.models.research_history import ResearchHistory
from app.models.user import User
from app.models.workflow_run import WorkflowRun
from app.schemas.workflow import (
    NodeExecutionResponse,
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

    # Get latest run's state
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
        state_snapshot=latest_run.state_snapshot if latest_run else None,
    )
