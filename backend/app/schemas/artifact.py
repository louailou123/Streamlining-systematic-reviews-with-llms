"""
LiRA Backend — Artifact API Schemas
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


class ArtifactResponse(BaseModel):
    id: UUID
    filename: str
    file_type: str
    mime_type: str
    file_size: int
    description: Optional[str]
    metadata_extra: Optional[Dict[str, Any]]
    created_at: datetime
    node_name: Optional[str] = None

    model_config = {"from_attributes": True}


class ArtifactListResponse(BaseModel):
    items: List[ArtifactResponse]
    total: int


class ApprovalResponse(BaseModel):
    id: UUID
    run_id: UUID
    research_id: UUID
    node_name: str
    approval_type: str
    status: str
    request_data: Optional[Dict[str, Any]]
    response_data: Optional[Dict[str, Any]]
    requested_at: datetime
    responded_at: Optional[datetime]

    model_config = {"from_attributes": True}
