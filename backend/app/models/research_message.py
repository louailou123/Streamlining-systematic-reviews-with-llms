"""
LiRA Backend — Research Message Model
Chat-timeline messages for the research workspace UI.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ResearchMessage(Base):
    __tablename__ = "research_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    research_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_histories.id", ondelete="CASCADE"), nullable=False, index=True
    )

    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user | system | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)

    message_type: Mapped[str] = mapped_column(
        String(50), default="text"
    )  # text | node_event | artifact | approval | error | workflow_completed

    metadata_extra: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    research = relationship("ResearchHistory", back_populates="messages")
