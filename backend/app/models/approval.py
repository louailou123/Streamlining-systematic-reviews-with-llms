"""
LiRA Backend — Approval Model
Tracks human-in-the-loop actions (e.g., ASReview screening).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False
    )
    research_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_histories.id", ondelete="CASCADE"), nullable=False, index=True
    )

    node_name: Mapped[str] = mapped_column(String(100), nullable=False)
    approval_type: Mapped[str] = mapped_column(String(100), nullable=False)  # asreview_screening

    status: Mapped[str] = mapped_column(
        String(50), default="pending"
    )  # pending | approved | rejected | expired

    request_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    response_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    uploaded_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("artifacts.id", ondelete="SET NULL"), nullable=True
    )

    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    workflow_run = relationship("WorkflowRun", back_populates="approvals")
    research = relationship("ResearchHistory", back_populates="approvals")
    uploaded_file = relationship("Artifact", foreign_keys=[uploaded_file_id])
