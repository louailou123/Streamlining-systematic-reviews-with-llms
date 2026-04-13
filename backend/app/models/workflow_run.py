"""
LiRA Backend — Workflow Run Model
Each execution attempt of a research pipeline.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    research_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_histories.id", ondelete="CASCADE"), nullable=False, index=True
    )

    run_number: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(
        String(50), default="pending"
    )  # pending | running | paused | completed | failed | cancelled

    state_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_traceback: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    research = relationship("ResearchHistory", back_populates="workflow_runs")
    node_executions = relationship("NodeExecution", back_populates="workflow_run", cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="workflow_run")
    approvals = relationship("Approval", back_populates="workflow_run")
