"""
LiRA Backend — Workflow API Schemas
Extended with per-node approval action schemas.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class WorkflowRunResponse(BaseModel):
    id: UUID
    research_id: UUID
    run_number: int
    status: str
    current_node: Optional[str] = None
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
    node_order: int = 0
    attempt_number: int = 1
    revision_number: int = 0
    started_at: datetime
    completed_at: Optional[datetime]
    approved_at: Optional[datetime] = None
    duration_ms: Optional[int]
    output_summary: Optional[Dict[str, Any]]
    logs: Optional[Any]
    error_message: Optional[str]
    feedback_text: Optional[str] = None

    model_config = {"from_attributes": True}


class WorkflowStateResponse(BaseModel):
    research_id: UUID
    status: str
    current_step: Optional[str]
    current_node: Optional[str] = None
    state_snapshot: Optional[Dict[str, Any]]


class StartWorkflowRequest(BaseModel):
    """Optional: force restart even if a run exists."""
    force_restart: bool = False


class ResumeWorkflowRequest(BaseModel):
    approval_id: UUID
    response_data: Optional[Dict[str, Any]] = None


class NodeApprovalAction(BaseModel):
    """User action on a node approval gate."""
    action: str = Field(..., pattern="^(continue|improve_result|retry)$")
    feedback: Optional[str] = None


class NodeReviewActionResponse(BaseModel):
    id: UUID
    node_execution_id: UUID
    research_id: UUID
    action_type: str
    feedback_text: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class PendingApprovalResponse(BaseModel):
    """Response for the pending approval query."""
    has_pending: bool
    approval_id: Optional[str] = None
    node_execution_id: Optional[str] = None
    node_name: Optional[str] = None
    step_label: Optional[str] = None
    description: Optional[str] = None
    approval_type: Optional[str] = None
