"""
LiRA Backend — Workflow Runner
Executes the LangGraph pipeline in a background thread, emitting
real-time events via SSE and persisting state + artifacts to the database.

Handles:
- Sequential node execution with event emission
- GraphInterrupt for human-in-the-loop (ASReview)
- State snapshot persistence after each node
- Artifact detection and registration
- Error handling and recovery
"""

import os
import time
import traceback
import threading
import uuid as uuid_mod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from app.workflow.engine import (
    build_lira_graph,
    NODE_STEP_MAP,
    NODE_DESCRIPTIONS,
)
from app.services.event_service import EventService

# Thread lock for CWD changes — ensures sequential node execution
# Safe for v1 scale (5-10 concurrent runs)
_cwd_lock = threading.Lock()

# MIME type mapping for artifacts
MIME_TYPES = {
    "csv": "text/csv",
    "json": "application/json",
    "ris": "application/x-research-info-systems",
    "md": "text/markdown",
    "png": "image/png",
    "jpg": "image/jpeg",
    "pdf": "application/pdf",
    "txt": "text/plain",
}


def _get_mime_type(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
    return MIME_TYPES.get(ext, "application/octet-stream")


def _get_file_type(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown"
    return ext


def _scan_new_files(work_dir: str, known_files: set) -> List[Dict[str, Any]]:
    """Scan work directory for files not in known_files set."""
    new_artifacts = []
    work_path = Path(work_dir)

    for f in work_path.rglob("*"):
        if f.is_file() and str(f) not in known_files:
            known_files.add(str(f))
            new_artifacts.append({
                "filename": f.name,
                "file_type": _get_file_type(f.name),
                "mime_type": _get_mime_type(f.name),
                "file_size": f.stat().st_size,
                "storage_path": str(f),
                "relative_path": str(f.relative_to(work_path)),
            })

    return new_artifacts


def _build_output_summary(state_update: Dict[str, Any]) -> Dict[str, Any]:
    """Build a concise output summary from a state update, excluding large fields."""
    summary = {}
    skip_keys = {"messages", "logs", "errors"}
    max_value_len = 500

    for key, value in state_update.items():
        if key in skip_keys:
            continue
        if isinstance(value, str) and len(value) > max_value_len:
            summary[key] = value[:max_value_len] + "..."
        elif isinstance(value, list) and len(value) > 10:
            summary[key] = f"[{len(value)} items]"
        elif isinstance(value, dict) and len(str(value)) > max_value_len:
            summary[key] = f"{{...{len(value)} keys}}"
        else:
            summary[key] = value

    return summary


def _serialize_state_snapshot(state: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize LiRAState to JSON-safe dict for DB storage."""
    snapshot = {}
    skip_keys = {"messages"}  # LangGraph messages are not JSON-serializable

    for key, value in state.items():
        if key in skip_keys:
            continue
        try:
            import json
            json.dumps(value)  # Test serializability
            snapshot[key] = value
        except (TypeError, ValueError):
            snapshot[key] = str(value)

    return snapshot


class WorkflowRunner:
    """
    Runs the LiRA pipeline graph and manages the full lifecycle:
    execution, event emission, state persistence, artifact tracking.
    """

    def __init__(
        self,
        research_id: str,
        run_id: str,
        work_dir: str,
        topic: str,
        timeframe: str = "3 months",
        databases: Optional[List[str]] = None,
        db_callbacks: Optional[Dict] = None,
    ):
        self.research_id = research_id
        self.run_id = run_id
        self.work_dir = work_dir
        self.topic = topic
        self.timeframe = timeframe
        self.databases = databases or [
            "Google Scholar", "arXiv", "OpenAlex", "PubMed", "CrossRef"
        ]
        self.db_callbacks = db_callbacks or {}
        self.events = EventService(research_id, run_id)
        self.known_files: set = set()
        self.checkpointer = MemorySaver()
        self.thread_id = f"research-{research_id}-run-{run_id}"

    def execute(self) -> Dict[str, Any]:
        """
        Execute the full pipeline. Runs synchronously (call from a thread).
        Returns the final state or raises on error.
        """
        # Ensure work directory exists
        Path(self.work_dir).mkdir(parents=True, exist_ok=True)

        # Scan existing files
        self._scan_existing_files()

        # Build the graph with checkpointer
        graph_builder = build_lira_graph()
        graph = graph_builder.compile(checkpointer=self.checkpointer)

        # Initial state
        initial_input = {
            "topic": self.topic,
            "timeframe": self.timeframe,
            "databases": self.databases,
            "messages": [],
            "logs": [],
        }

        config = {
            "configurable": {"thread_id": self.thread_id},
        }

        self.events.log_message("Pipeline started")
        self._notify_db("run_started")

        try:
            final_state = self._stream_graph(graph, initial_input, config)
            self.events.workflow_completed(
                f"Pipeline completed. Current step: {final_state.get('current_step', 'Done')}"
            )
            self._notify_db("run_completed", state=final_state)
            return final_state

        except GraphInterruptException as e:
            # Human-in-the-loop: ASReview screening
            self.events.log_message(f"Pipeline paused: {e.interrupt_data.get('message', 'Approval required')}")
            self._notify_db("run_paused", interrupt_data=e.interrupt_data)
            return {"status": "paused", "interrupt": e.interrupt_data}

        except Exception as e:
            error_msg = str(e)
            error_tb = traceback.format_exc()
            self.events.workflow_failed(error_msg)
            self._notify_db("run_failed", error=error_msg, traceback=error_tb)
            raise

    def resume(self, resume_value: Any) -> Dict[str, Any]:
        """
        Resume a paused pipeline after human-in-the-loop action.
        """
        graph_builder = build_lira_graph()
        graph = graph_builder.compile(checkpointer=self.checkpointer)

        config = {
            "configurable": {"thread_id": self.thread_id},
        }

        self.events.log_message("Pipeline resuming after approval")
        self._notify_db("run_resumed")

        try:
            final_state = self._stream_graph(
                graph,
                Command(resume=resume_value),
                config,
            )
            self.events.workflow_completed(
                f"Pipeline completed. Current step: {final_state.get('current_step', 'Done')}"
            )
            self._notify_db("run_completed", state=final_state)
            return final_state

        except GraphInterruptException as e:
            self.events.log_message(f"Pipeline paused again: {e.interrupt_data.get('message', '')}")
            self._notify_db("run_paused", interrupt_data=e.interrupt_data)
            return {"status": "paused", "interrupt": e.interrupt_data}

        except Exception as e:
            error_msg = str(e)
            error_tb = traceback.format_exc()
            self.events.workflow_failed(error_msg)
            self._notify_db("run_failed", error=error_msg, traceback=error_tb)
            raise

    def _stream_graph(self, graph, input_data, config) -> Dict[str, Any]:
        """
        Stream graph execution node-by-node, emitting events for each.
        Changes CWD to work_dir while executing (protected by lock).
        """
        final_state = {}

        with _cwd_lock:
            original_cwd = os.getcwd()
            try:
                os.chdir(self.work_dir)

                for event in graph.stream(input_data, config, stream_mode="updates"):
                    for node_name, state_update in event.items():
                        if node_name == "__interrupt__":
                            # Handle LangGraph interrupt
                            interrupt_data = state_update
                            if isinstance(interrupt_data, list) and interrupt_data:
                                interrupt_data = interrupt_data[0]
                                if hasattr(interrupt_data, "value"):
                                    interrupt_data = interrupt_data.value
                            raise GraphInterruptException(interrupt_data)

                        step_label = NODE_STEP_MAP.get(node_name, "")
                        description = NODE_DESCRIPTIONS.get(node_name, node_name)

                        # Emit node started
                        start_time = time.time()
                        self.events.node_started(node_name, step_label, description)

                        # Calculate duration
                        duration_ms = int((time.time() - start_time) * 1000)

                        # Extract logs from state update
                        node_logs = []
                        if isinstance(state_update, dict):
                            node_logs = state_update.get("logs", [])
                            final_state.update(state_update)

                        # Build output summary
                        output_summary = _build_output_summary(state_update) if isinstance(state_update, dict) else {}

                        # Emit node completed
                        self.events.node_completed(
                            node_name=node_name,
                            step_label=step_label,
                            output_summary=output_summary,
                            logs=node_logs[-3:] if node_logs else [],  # last 3 logs
                            duration_ms=duration_ms,
                        )

                        # Record node execution in DB
                        self._notify_db(
                            "node_completed",
                            node_name=node_name,
                            step_label=step_label,
                            output_summary=output_summary,
                            logs=node_logs,
                            duration_ms=duration_ms,
                        )

                        # Scan for new files after node completion
                        new_files = _scan_new_files(self.work_dir, self.known_files)
                        for artifact_info in new_files:
                            self.events.artifact_created(
                                filename=artifact_info["filename"],
                                file_type=artifact_info["file_type"],
                                node_name=node_name,
                            )
                            self._notify_db("artifact_created", artifact=artifact_info, node_name=node_name)

            finally:
                os.chdir(original_cwd)

        return final_state

    def _scan_existing_files(self) -> None:
        """Pre-scan work directory to track existing files."""
        work_path = Path(self.work_dir)
        if work_path.exists():
            for f in work_path.rglob("*"):
                if f.is_file():
                    self.known_files.add(str(f))

    def _notify_db(self, event_type: str, **kwargs) -> None:
        """Call registered database callback for persistence."""
        callback = self.db_callbacks.get(event_type)
        if callback:
            try:
                callback(**kwargs)
            except Exception as e:
                print(f"[Runner] DB callback error ({event_type}): {e}")


class GraphInterruptException(Exception):
    """Raised when the graph hits an interrupt() for human-in-the-loop."""
    def __init__(self, interrupt_data: Any):
        self.interrupt_data = interrupt_data
        super().__init__(f"Graph interrupted: {interrupt_data}")
