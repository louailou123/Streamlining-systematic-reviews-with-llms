"""
LiRA Backend — Research API Schemas
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Requests ─────────────────────────────────────────────────

class CreateResearchRequest(BaseModel):
    topic: str = Field(min_length=10, max_length=2000)
    timeframe: str = Field(default="3 months", max_length=100)
    databases: List[str] = Field(
        default=["Google Scholar", "arXiv", "OpenAlex", "PubMed", "CrossRef"]
    )


# ── Responses ────────────────────────────────────────────────

class ResearchSummaryResponse(BaseModel):
    id: UUID
    title: str
    topic: str
    status: str
    current_step: Optional[str]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    latest_summary: Optional[str]

    model_config = {"from_attributes": True}


class ResearchDetailResponse(BaseModel):
    id: UUID
    title: str
    topic: str
    timeframe: str
    databases: Optional[List[str]]
    status: str
    current_step: Optional[str]
    started_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    latest_summary: Optional[str]
    latest_error: Optional[str]
    pipeline_version: str

    model_config = {"from_attributes": True}


class ResearchMessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    message_type: str
    metadata_extra: Optional[Dict[str, Any]]
    created_at: datetime

    model_config = {"from_attributes": True}


class ResearchListResponse(BaseModel):
    items: List[ResearchSummaryResponse]
    total: int
