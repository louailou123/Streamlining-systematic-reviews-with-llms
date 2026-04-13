"""
LiRA Backend — Node Execution Model
Records each LangGraph node's execution within a workflow run.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class NodeExecution(Base):
    __tablename__ = "node_executions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    node_name: Mapped[str] = mapped_column(String(100), nullable=False)
    step_label: Mapped[str | None] = mapped_column(String(50), nullable=True)

    status: Mapped[str] = mapped_column(
        String(50), default="running"
    )  # running | completed | failed

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    input_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    logs: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # array of strings

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    workflow_run = relationship("WorkflowRun", back_populates="node_executions")
    artifacts = relationship("Artifact", back_populates="node_execution")
