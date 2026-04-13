"""
LiRA Backend — Research API Routes
CRUD for research histories + message timeline.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.session import get_db
from app.models.research_history import ResearchHistory
from app.models.research_message import ResearchMessage
from app.models.user import User
from app.schemas.research import (
    CreateResearchRequest,
    ResearchDetailResponse,
    ResearchListResponse,
    ResearchMessageResponse,
    ResearchSummaryResponse,
)

router = APIRouter(prefix="/research", tags=["Research"])


async def _get_research_or_404(
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


@router.get("", response_model=ResearchListResponse)
async def list_research(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List current user's research histories, newest first."""
    base_query = select(ResearchHistory).where(ResearchHistory.user_id == current_user.id)

    # Count
    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar() or 0

    # Fetch
    result = await db.execute(
        base_query.order_by(desc(ResearchHistory.updated_at)).offset(skip).limit(limit)
    )
    items = result.scalars().all()

    return ResearchListResponse(
        items=[ResearchSummaryResponse.model_validate(r) for r in items],
        total=total,
    )


@router.post("", response_model=ResearchDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_research(
    body: CreateResearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new research project. Workflow starts automatically."""
    # Auto-generate title from topic (first 80 chars)
    title = body.topic[:80].strip()
    if len(body.topic) > 80:
        title += "..."

    research = ResearchHistory(
        user_id=current_user.id,
        title=title,
        topic=body.topic,
        timeframe=body.timeframe,
        databases=body.databases,
        status="pending",
    )
    db.add(research)

    # Add initial user message to timeline
    user_msg = ResearchMessage(
        research_id=research.id,
        role="user",
        content=body.topic,
        message_type="text",
    )
    db.add(user_msg)

    await db.commit()
    await db.refresh(research)

    # Auto-start workflow in background
    from app.services.workflow_service import WorkflowService
    workflow_service = WorkflowService(db)
    await workflow_service.start_workflow(research)
    await db.refresh(research)

    return research


@router.get("/{research_id}", response_model=ResearchDetailResponse)
async def get_research(
    research_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed information about a research project."""
    research = await _get_research_or_404(research_id, current_user, db)
    return research


@router.delete("/{research_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_research(
    research_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a research project and all associated data."""
    research = await _get_research_or_404(research_id, current_user, db)
    await db.delete(research)
    await db.commit()


@router.get("/{research_id}/messages", response_model=list[ResearchMessageResponse])
async def get_messages(
    research_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get chat timeline messages for a research project."""
    _ = await _get_research_or_404(research_id, current_user, db)

    result = await db.execute(
        select(ResearchMessage)
        .where(ResearchMessage.research_id == research_id)
        .order_by(ResearchMessage.created_at)
        .offset(skip)
        .limit(limit)
    )
    messages = result.scalars().all()
    return [ResearchMessageResponse.model_validate(m) for m in messages]
