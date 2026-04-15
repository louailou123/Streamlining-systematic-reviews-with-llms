"""
LiRA Backend — Workflow Runner
Executes the LangGraph pipeline in a background thread, emitting
real-time events via WebSocket and persisting state + artifacts to the database.

Handles:
- Sequential node execution with event emission
- Per-node approval gates (interrupt after every node)
- GraphInterrupt for human-in-the-loop (approval + ASReview)
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

from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
from langgraph.types import Command

from app.workflow.engine import (
    build_lira_graph,
    NODE_STEP_MAP,
    NODE_DESCRIPTIONS,
    GATE_NODE_NAMES,
)
from app.services.event_service import EventService
from logger import LiRALogger

# Thread lock for CWD changes — ensures sequential node execution
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
    """Build a concise output summary from a state update, parsing LLM messages natively."""
    summary = {}
    skip_keys = {"logs", "errors", "user_feedback", "current_approval_node"}
    max_value_len = 500

    for key, value in state_update.items():
        if key in skip_keys:
            continue
            
        if key == "messages":
            safe_messages = []
            for msg in value:
                msg_type = msg.__class__.__name__
                content = getattr(msg, "content", "")
                if not isinstance(content, str):
                    content = str(content)
                
                msg_dict = {
                    "type": msg_type,
                    "content": content[:1500] + ("..." if len(content) > 1500 else ""),
                }
                
                tool_calls = getattr(msg, "tool_calls", None)
                if tool_calls:
                    safe_tc = []
                    for tc in tool_calls:
                        safe_tc.append({
                            "name": tc.get("name", "unknown"),
                            "args": tc.get("args", {})
                        })
                    msg_dict["tool_calls"] = safe_tc
                    
                usage = getattr(msg, "usage_metadata", None)
                if usage:
                    msg_dict["usage_metadata"] = usage
                    
                safe_messages.append(msg_dict)
            summary["messages"] = safe_messages
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
    execution, event emission, state persistence, artifact tracking,
    and per-node approval gates.
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
        # Ensure work directory exists
        Path(self.work_dir).mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(os.path.join(self.work_dir, "checkpoints.sqlite"), check_same_thread=False)
        self.checkpointer = SqliteSaver(self.conn)
        self.checkpointer.setup()
        self.thread_id = f"research-{research_id}-run-{run_id}"
        
        # HTML Logger (wrapped to survive hot-reload I/O errors)
        try:
            self.html_logger = LiRALogger(base_dir=self.work_dir)
        except Exception:
            self.html_logger = None

    def execute(self) -> Dict[str, Any]:
        """
        Execute the full pipeline. Runs synchronously (call from a thread).
        Returns the final state or raises on interrupts/errors.
        """
        Path(self.work_dir).mkdir(parents=True, exist_ok=True)
        self._scan_existing_files()

        graph_builder = build_lira_graph()
        graph = graph_builder.compile(checkpointer=self.checkpointer)

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
        
        self._safe_log('log_initial_input', initial_input)
        self._safe_log('log_graph_structure', graph_builder)

        try:
            result = self._stream_graph(graph, initial_input, config)
            return result

        except NodeApprovalInterrupt as e:
            approval_id = str(uuid_mod.uuid4())
            node_execution_id = str(uuid_mod.uuid4())
            self._notify_db("node_approval_required",
                node_name=e.node_name,
                step_label=e.step_label,
                description=e.description,
                approval_id=approval_id,
                node_execution_id=node_execution_id,
            )
            raise

        except GraphInterruptException as e:
            # Legacy ASReview human-in-the-loop interrupt
            interrupt_data = e.interrupt_data
            if isinstance(interrupt_data, tuple):
                interrupt_data = interrupt_data[0]
            if hasattr(interrupt_data, "value"):
                interrupt_data = interrupt_data.value
            if not isinstance(interrupt_data, dict):
                interrupt_data = {"message": str(interrupt_data)}

            self.events.log_message(f"Pipeline paused: {interrupt_data.get('message', 'Approval required')}")
            self._notify_db("run_paused", interrupt_data=interrupt_data)
            self._safe_log('close')
            raise GraphInterruptException(interrupt_data)

        except Exception as e:
            error_msg = str(e)
            error_tb = traceback.format_exc()
            self.events.workflow_failed(error_msg)
            self._notify_db("run_failed", error=error_msg, traceback=error_tb)
            self._safe_log('log_error', e)
            self._safe_log('close')
            raise

    def resume(self, resume_value: Any) -> Dict[str, Any]:
        """
        Resume a paused pipeline after user action (continue/improve/retry).
        resume_value should be:
          - {"action": "continue"} for approval
          - {"action": "improve_result", "feedback": "..."} for revision
          - {"action": "retry"} for retrying a failed node
          - a string path for legacy ASReview file upload resume
        """
        graph_builder = build_lira_graph()
        graph = graph_builder.compile(checkpointer=self.checkpointer)

        config = {
            "configurable": {"thread_id": self.thread_id},
        }

        self.events.log_message("Pipeline resuming")
        self._notify_db("run_resumed")

        try:
            result = self._stream_graph(
                graph,
                Command(resume=resume_value),
                config,
            )
            return result

        except NodeApprovalInterrupt as e:
            approval_id = str(uuid_mod.uuid4())
            node_execution_id = str(uuid_mod.uuid4())
            self._notify_db("node_approval_required",
                node_name=e.node_name,
                step_label=e.step_label,
                description=e.description,
                approval_id=approval_id,
                node_execution_id=node_execution_id,
            )
            raise

        except GraphInterruptException as e:
            interrupt_data = e.interrupt_data
            if isinstance(interrupt_data, tuple):
                interrupt_data = interrupt_data[0]
            if hasattr(interrupt_data, "value"):
                interrupt_data = interrupt_data.value
            if not isinstance(interrupt_data, dict):
                interrupt_data = {"message": str(interrupt_data)}

            self.events.log_message(f"Pipeline paused: {interrupt_data.get('message', '')}")
            self._notify_db("run_paused", interrupt_data=interrupt_data)
            raise GraphInterruptException(interrupt_data)

        except Exception as e:
            error_msg = str(e)
            error_tb = traceback.format_exc()
            self.events.workflow_failed(error_msg)
            self._notify_db("run_failed", error=error_msg, traceback=error_tb)
            self._safe_log('log_error', e)
            self._safe_log('close')
            raise

    def _stream_graph(self, graph, input_data, config) -> Dict[str, Any]:
        """
        Stream graph execution node-by-node, emitting events for each.
        Changes CWD to work_dir while executing (protected by lock).
        Raises NodeApprovalInterrupt for approval gates.
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
                            # LangGraph returns interrupt data as a TUPLE of Interrupt objects
                            interrupt_data = state_update

                            # Unwrap tuple/list → single element
                            if isinstance(interrupt_data, (list, tuple)) and interrupt_data:
                                interrupt_data = interrupt_data[0]

                            # Unwrap Interrupt object → its .value dict
                            if hasattr(interrupt_data, "value"):
                                interrupt_data = interrupt_data.value

                            # If still wrapped (nested), try again
                            if isinstance(interrupt_data, (list, tuple)) and interrupt_data:
                                interrupt_data = interrupt_data[0]
                            if hasattr(interrupt_data, "value"):
                                interrupt_data = interrupt_data.value

                            print(f"[Runner] Interrupt data parsed: {type(interrupt_data)} = {interrupt_data}")

                            # Check if this is a per-node approval gate interrupt
                            if isinstance(interrupt_data, dict) and interrupt_data.get("type") == "node_approval":
                                raise NodeApprovalInterrupt(
                                    node_name=interrupt_data["node_name"],
                                    step_label=interrupt_data.get("step_label", ""),
                                    description=interrupt_data.get("description", ""),
                                )
                            
                            # Legacy interrupt (ASReview file upload, etc.)
                            raise GraphInterruptException(interrupt_data)

                        # Skip gate nodes from heavy processing (they don't produce real output)
                        if node_name in GATE_NODE_NAMES:
                            continue

                        step_label = NODE_STEP_MAP.get(node_name, "")
                        description = NODE_DESCRIPTIONS.get(node_name, node_name)

                        # Emit node started
                        start_time = time.time()
                        self.events.node_started(node_name, step_label, description)
                        self._safe_log('node_start', node_name)

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
                            logs=node_logs[-3:] if node_logs else [],
                            duration_ms=duration_ms,
                        )
                        self._safe_log('node_end', node_name, state_update if isinstance(state_update, dict) else {})

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

        # If we got here, the full pipeline completed
        self.events.workflow_completed(
            f"Pipeline completed. Current step: {final_state.get('current_step', 'Done')}"
        )
        self._notify_db("run_completed", state=final_state)
        self._safe_log('log_final_state', final_state)
        self._safe_log('close')

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
            except Exception:
                pass  # Don't let DB callback errors crash the pipeline

    def _safe_log(self, method: str, *args, **kwargs) -> None:
        """Call html_logger method safely — survives I/O errors from hot-reload."""
        if not self.html_logger:
            return
        try:
            getattr(self.html_logger, method)(*args, **kwargs)
        except (ValueError, OSError, IOError):
            pass  # I/O on closed file — uvicorn hot-reload artifact


class GraphInterruptException(Exception):
    """Raised when the graph hits a legacy interrupt (ASReview file upload)."""
    def __init__(self, interrupt_data: Any):
        self.interrupt_data = interrupt_data
        super().__init__(f"Graph interrupted: {interrupt_data}")


class NodeApprovalInterrupt(Exception):
    """Raised when a per-node approval gate triggers an interrupt."""
    def __init__(self, node_name: str, step_label: str = "", description: str = ""):
        self.node_name = node_name
        self.step_label = step_label
        self.description = description
        super().__init__(f"Node approval required: {node_name}")
