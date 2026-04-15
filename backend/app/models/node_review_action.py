"""
LiRA Backend — Node Review Action Model
Tracks every user action (continue, improve, retry) on a node execution.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class NodeReviewAction(Base):
    __tablename__ = "node_review_actions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    node_execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("node_executions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    research_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_histories.id", ondelete="CASCADE"), nullable=False, index=True
    )

    action_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # continue | improve_result | retry

    feedback_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    node_execution = relationship("NodeExecution", back_populates="review_actions")
    research = relationship("ResearchHistory")
