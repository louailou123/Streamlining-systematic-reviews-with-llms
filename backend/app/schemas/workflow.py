"""
LiRA Backend — Workflow API Schemas
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


class WorkflowRunResponse(BaseModel):
    id: UUID
    research_id: UUID
    run_number: int
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    error_message: Optional[str]

    model_config = {"from_attributes": True}


class NodeExecutionResponse(BaseModel):
    id: UUID
    run_id: UUID
    node_name: str
    step_label: Optional[str]
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    duration_ms: Optional[int]
    output_summary: Optional[Dict[str, Any]]
    logs: Optional[Any]
    error_message: Optional[str]

    model_config = {"from_attributes": True}


class WorkflowStateResponse(BaseModel):
    research_id: UUID
    status: str
    current_step: Optional[str]
    state_snapshot: Optional[Dict[str, Any]]


class StartWorkflowRequest(BaseModel):
    """Optional: force restart even if a run exists."""
    force_restart: bool = False


class ResumeWorkflowRequest(BaseModel):
    approval_id: UUID
    response_data: Optional[Dict[str, Any]] = None
