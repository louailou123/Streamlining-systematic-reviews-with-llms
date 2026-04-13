"""
LiRA Backend — Research Service
Business logic for research CRUD and message management.
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.research_history import ResearchHistory
from app.models.research_message import ResearchMessage
from app.models.artifact import Artifact


class ResearchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_for_user(
        self, user_id: UUID, skip: int = 0, limit: int = 20
    ) -> tuple[List[ResearchHistory], int]:
        """List research histories for a user with total count."""
        base_query = select(ResearchHistory).where(ResearchHistory.user_id == user_id)

        count_result = await self.db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = count_result.scalar() or 0

        result = await self.db.execute(
            base_query.order_by(desc(ResearchHistory.updated_at)).offset(skip).limit(limit)
        )
        items = result.scalars().all()
        return list(items), total

    async def get_for_user(self, research_id: UUID, user_id: UUID) -> Optional[ResearchHistory]:
        result = await self.db.execute(
            select(ResearchHistory).where(
                ResearchHistory.id == research_id,
                ResearchHistory.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        user_id: UUID,
        topic: str,
        timeframe: str = "3 months",
        databases: Optional[List[str]] = None,
    ) -> ResearchHistory:
        title = topic[:80].strip()
        if len(topic) > 80:
            title += "..."

        research = ResearchHistory(
            user_id=user_id,
            title=title,
            topic=topic,
            timeframe=timeframe,
            databases=databases or ["Google Scholar", "arXiv", "OpenAlex", "PubMed", "CrossRef"],
            status="pending",
        )
        self.db.add(research)

        # Initial user message
        msg = ResearchMessage(
            research_id=research.id,
            role="user",
            content=topic,
            message_type="text",
        )
        self.db.add(msg)

        await self.db.commit()
        await self.db.refresh(research)
        return research

    async def add_message(
        self,
        research_id: UUID,
        role: str,
        content: str,
        message_type: str = "text",
        metadata: Optional[dict] = None,
    ) -> ResearchMessage:
        msg = ResearchMessage(
            research_id=research_id,
            role=role,
            content=content,
            message_type=message_type,
            metadata_extra=metadata,
        )
        self.db.add(msg)
        await self.db.commit()
        await self.db.refresh(msg)
        return msg

    async def get_messages(
        self, research_id: UUID, skip: int = 0, limit: int = 200
    ) -> List[ResearchMessage]:
        result = await self.db.execute(
            select(ResearchMessage)
            .where(ResearchMessage.research_id == research_id)
            .order_by(ResearchMessage.created_at)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_artifacts(self, research_id: UUID) -> List[Artifact]:
        result = await self.db.execute(
            select(Artifact)
            .where(Artifact.research_id == research_id)
            .order_by(Artifact.created_at)
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        research_id: UUID,
        status: str,
        current_step: Optional[str] = None,
        summary: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        result = await self.db.execute(
            select(ResearchHistory).where(ResearchHistory.id == research_id)
        )
        research = result.scalar_one_or_none()
        if research:
            research.status = status
            if current_step is not None:
                research.current_step = current_step
            if summary is not None:
                research.latest_summary = summary
            if error is not None:
                research.latest_error = error
            if status == "completed":
                research.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
