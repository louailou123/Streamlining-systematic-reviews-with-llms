"""
LiRA Backend — Event Service
Centralized event publishing for WebSocket and database persistence.
Extended with per-node approval events.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from app.api.v1.events import publish_event


class EventService:
    """Publishes workflow events to WebSocket subscribers and optionally persists them."""

    def __init__(self, research_id: str, run_id: Optional[str] = None):
        self.research_id = str(research_id)
        self.run_id = str(run_id) if run_id else None

    def _build_event(
        self,
        event_type: str,
        node_name: Optional[str] = None,
        step_label: Optional[str] = None,
        message: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> dict:
        return {
            "event_type": event_type,
            "research_id": self.research_id,
            "run_id": self.run_id,
            "node_name": node_name,
            "step_label": step_label,
            "message": message,
            "data": data or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def emit(
        self,
        event_type: str,
        node_name: Optional[str] = None,
        step_label: Optional[str] = None,
        message: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Publish event to SSE subscribers."""
        event = self._build_event(event_type, node_name, step_label, message, data)
        publish_event(self.research_id, event)

    def node_started(self, node_name: str, step_label: str = "", description: str = "") -> None:
        self.emit(
            "NODE_STARTED",
            node_name=node_name,
            step_label=step_label,
            message=description or f"Executing {node_name}...",
        )

    def node_completed(
        self,
        node_name: str,
        step_label: str = "",
        output_summary: Optional[Dict] = None,
        logs: Optional[list] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        self.emit(
            "NODE_COMPLETED",
            node_name=node_name,
            step_label=step_label,
            message=f"Completed {node_name}",
            data={
                "output_summary": output_summary or {},
                "logs": logs or [],
                "duration_ms": duration_ms,
            },
        )

    def node_failed(self, node_name: str, step_label: str = "", error: str = "") -> None:
        self.emit(
            "NODE_FAILED",
            node_name=node_name,
            step_label=step_label,
            message=f"Failed: {error}",
            data={"error": error},
        )

    def node_waiting_for_approval(
        self,
        node_name: str,
        step_label: str = "",
        description: str = "",
        approval_id: Optional[str] = None,
        node_execution_id: Optional[str] = None,
        approval_type: str = "node_approval",
        output_summary: Optional[Dict] = None,
    ) -> None:
        """Emit event when a node is waiting for user approval."""
        self.emit(
            "NODE_WAITING_FOR_APPROVAL",
            node_name=node_name,
            step_label=step_label,
            message=f"Waiting for approval: {description}",
            data={
                "description": description,
                "approval_id": approval_id,
                "node_execution_id": node_execution_id,
                "approval_type": approval_type,
                "output_summary": output_summary or {},
            },
        )

    def node_revision_started(
        self,
        node_name: str,
        step_label: str = "",
        feedback: str = "",
    ) -> None:
        """Emit event when a node revision (improve_result) starts."""
        self.emit(
            "NODE_REVISION_STARTED",
            node_name=node_name,
            step_label=step_label,
            message=f"Revising {node_name} with feedback",
            data={"feedback": feedback},
        )

    def node_retry_started(
        self,
        node_name: str,
        step_label: str = "",
        attempt: int = 1,
    ) -> None:
        """Emit event when a node retry starts."""
        self.emit(
            "NODE_RETRY_STARTED",
            node_name=node_name,
            step_label=step_label,
            message=f"Retrying {node_name} (attempt {attempt})",
            data={"attempt": attempt},
        )

    def log_message(self, message: str, node_name: Optional[str] = None) -> None:
        self.emit("LOG_MESSAGE", node_name=node_name, message=message)

    def artifact_created(
        self,
        filename: str,
        file_type: str,
        node_name: Optional[str] = None,
        artifact_id: Optional[str] = None,
    ) -> None:
        self.emit(
            "ARTIFACT_CREATED",
            node_name=node_name,
            message=f"Created {filename}",
            data={
                "filename": filename,
                "file_type": file_type,
                "artifact_id": artifact_id,
            },
        )

    def approval_required(
        self,
        approval_id: str,
        node_name: str,
        approval_type: str,
        request_data: Optional[Dict] = None,
    ) -> None:
        self.emit(
            "APPROVAL_REQUIRED",
            node_name=node_name,
            message=f"Human action required: {approval_type}",
            data={
                "approval_id": approval_id,
                "approval_type": approval_type,
                "request_data": request_data or {},
            },
        )

    def workflow_completed(self, summary: str = "") -> None:
        self.emit(
            "WORKFLOW_COMPLETED",
            message=summary or "Pipeline completed successfully",
        )

    def workflow_failed(self, error: str = "") -> None:
        self.emit(
            "WORKFLOW_FAILED",
            message=f"Pipeline failed: {error}",
            data={"error": error},
        )
