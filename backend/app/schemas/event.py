"""
LiRA Backend — SSE Event Schemas
"""

from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel


class WorkflowEvent(BaseModel):
    """Schema for events sent over SSE."""
    event_type: str  # NODE_STARTED | NODE_COMPLETED | NODE_FAILED |
                     # LOG_MESSAGE | ARTIFACT_CREATED | APPROVAL_REQUIRED |
                     # WORKFLOW_COMPLETED | WORKFLOW_FAILED
    research_id: str
    run_id: Optional[str] = None
    node_name: Optional[str] = None
    step_label: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None
