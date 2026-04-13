"""
LiRA Backend — Research History Model
Top-level entity: one per user research project.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ResearchHistory(Base):
    __tablename__ = "research_histories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    timeframe: Mapped[str] = mapped_column(String(100), default="3 months")
    databases: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    status: Mapped[str] = mapped_column(
        String(50), default="pending", index=True
    )  # pending | running | paused | completed | failed
    current_step: Mapped[str | None] = mapped_column(String(100), nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    latest_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    latest_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    pipeline_version: Mapped[str] = mapped_column(String(20), default="1.0")

    # Relationships
    user = relationship("User", back_populates="research_histories")
    workflow_runs = relationship("WorkflowRun", back_populates="research", cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="research", cascade="all, delete-orphan")
    approvals = relationship("Approval", back_populates="research", cascade="all, delete-orphan")
    messages = relationship("ResearchMessage", back_populates="research", cascade="all, delete-orphan")
