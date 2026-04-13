"""
LiRA Backend — Artifact Model
Tracks all generated files (CSV, JSON, PNG, MD, RIS) per workflow run.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_runs.id", ondelete="SET NULL"), nullable=True
    )
    node_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("node_executions.id", ondelete="SET NULL"), nullable=True
    )
    research_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_histories.id", ondelete="CASCADE"), nullable=False, index=True
    )

    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)  # csv | json | ris | md | png | pdf
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0)

    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_extra: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    workflow_run = relationship("WorkflowRun", back_populates="artifacts")
    node_execution = relationship("NodeExecution", back_populates="artifacts")
    research = relationship("ResearchHistory", back_populates="artifacts")
