"""
Web-only message budget guard for the LangGraph workflow.

This module estimates token usage heuristically, tracks a rolling
per-model token ledger, trims older messages when pressure is high,
and waits briefly when the projected rolling-minute budget is still
too high after trimming.
"""

from __future__ import annotations

import json
import math
import os
import re
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Callable, Sequence

from langchain_core.messages import RemoveMessage

DEFAULT_SOFT_TPM_LIMIT = int(os.getenv("WEB_WORKFLOW_SOFT_TPM_LIMIT", "10000"))
WINDOW_SECONDS = 60.0
MIN_WAIT_SECONDS = 0.25
MAX_WAIT_SLICE_SECONDS = 2.0
MESSAGE_OVERHEAD_TOKENS = 12
TOOL_CALL_SURCHARGE_TOKENS = 24
KNOWN_MODEL_TPM_LIMITS = {
    "llama-3.3-70b-versatile": 12_000,
    "meta-llama/llama-4-scout-17b-16e-instruct": 30_000,
    "llama-4-scout-17b-16e-instruct": 30_000,
}

_ledger_lock = threading.Lock()
_token_ledger: dict[str, deque[tuple[float, int]]] = defaultdict(deque)
_soft_tpm_limits: dict[str, int] = {}


@dataclass(frozen=True)
class GuardDecision:
    model_name: str
    window_tokens: int
    request_tokens: int
    projected_tokens: int
    allowed_request_tokens: int
    wait_seconds: float


def _now() -> float:
    return time.monotonic()


def _base_model_name(model_name: str) -> str:
    return model_name.split("::", 1)[0]


def _get_soft_tpm_limit(model_name: str) -> int:
    base_name = _base_model_name(model_name)
    with _ledger_lock:
        if model_name in _soft_tpm_limits:
            return _soft_tpm_limits[model_name]
        if base_name in _soft_tpm_limits:
            return _soft_tpm_limits[base_name]

    known_limit = KNOWN_MODEL_TPM_LIMITS.get(base_name)
    if known_limit:
        return max(1_000, int(known_limit * 0.75))

    return DEFAULT_SOFT_TPM_LIMIT


def _remember_soft_tpm_limit(model_name: str, provider_limit: int) -> int:
    safe_limit = max(1_000, int(provider_limit * 0.75))
    base_name = _base_model_name(model_name)

    with _ledger_lock:
        _soft_tpm_limits[model_name] = safe_limit
        _soft_tpm_limits[base_name] = safe_limit

    return safe_limit


def _purge_expired(entries: deque[tuple[float, int]], now: float) -> None:
    while entries and (now - entries[0][0]) >= WINDOW_SECONDS:
        entries.popleft()


def _serialize_message(message: Any) -> str:
    payload = {
        "type": message.__class__.__name__,
        "id": getattr(message, "id", None),
        "name": getattr(message, "name", None),
        "tool_call_id": getattr(message, "tool_call_id", None),
        "content": getattr(message, "content", None),
        "tool_calls": getattr(message, "tool_calls", None),
        "additional_kwargs": getattr(message, "additional_kwargs", None),
        "usage_metadata": getattr(message, "usage_metadata", None),
    }
    return json.dumps(payload, ensure_ascii=False, default=str, sort_keys=True)


def estimate_message_tokens(message: Any) -> int:
    serialized = _serialize_message(message)
    tool_calls = getattr(message, "tool_calls", None) or []
    return max(
        1,
        math.ceil(len(serialized) / 4)
        + MESSAGE_OVERHEAD_TOKENS
        + (len(tool_calls) * TOOL_CALL_SURCHARGE_TOKENS),
    )


def estimate_messages_tokens(messages: Sequence[Any]) -> int:
    return sum(estimate_message_tokens(message) for message in messages)


def _estimate_wait_seconds(
    entries: deque[tuple[float, int]],
    excess_tokens: int,
    now: float,
) -> float:
    if excess_tokens <= 0 or not entries:
        return 0.0

    released = 0
    for timestamp, tokens in entries:
        released += tokens
        if released >= excess_tokens:
            return max((timestamp + WINDOW_SECONDS) - now, MIN_WAIT_SECONDS)

    return WINDOW_SECONDS


def project_tpm_pressure(model_name: str, request_tokens: int) -> GuardDecision:
    now = _now()
    soft_limit = _get_soft_tpm_limit(model_name)
    with _ledger_lock:
        entries = _token_ledger[model_name]
        _purge_expired(entries, now)
        window_tokens = sum(tokens for _, tokens in entries)

    projected_tokens = window_tokens + request_tokens
    allowed_request_tokens = max(soft_limit - window_tokens, 0)
    excess_tokens = max(projected_tokens - soft_limit, 0)

    with _ledger_lock:
        wait_seconds = _estimate_wait_seconds(_token_ledger[model_name], excess_tokens, now)

    return GuardDecision(
        model_name=model_name,
        window_tokens=window_tokens,
        request_tokens=request_tokens,
        projected_tokens=projected_tokens,
        allowed_request_tokens=allowed_request_tokens,
        wait_seconds=wait_seconds,
    )


def reserve_tokens(model_name: str, request_tokens: int) -> None:
    if request_tokens <= 0:
        return

    now = _now()
    with _ledger_lock:
        entries = _token_ledger[model_name]
        _purge_expired(entries, now)
        entries.append((now, request_tokens))


def trim_messages_to_budget(
    messages: Sequence[Any],
    allowed_tokens: int,
) -> tuple[list[Any], list[str]]:
    if not messages:
        return [], []

    kept_reversed: list[Any] = []
    kept_tokens = 0

    for message in reversed(messages):
        message_tokens = estimate_message_tokens(message)
        projected = kept_tokens + message_tokens

        if projected <= allowed_tokens or not kept_reversed:
            kept_reversed.append(message)
            kept_tokens = projected

    kept_messages = list(reversed(kept_reversed))
    kept_object_ids = {id(message) for message in kept_messages}
    removed_ids = [
        message.id
        for message in messages
        if getattr(message, "id", None) and id(message) not in kept_object_ids
    ]

    return kept_messages, removed_ids


def wait_for_tpm_budget(model_name: str, request_tokens: int) -> float:
    total_wait = 0.0
    soft_limit = _get_soft_tpm_limit(model_name)

    while True:
        decision = project_tpm_pressure(model_name, request_tokens)
        if decision.projected_tokens <= soft_limit:
            return total_wait

        wait_slice = min(
            max(decision.wait_seconds, MIN_WAIT_SECONDS),
            MAX_WAIT_SLICE_SECONDS,
        )
        time.sleep(wait_slice)
        total_wait += wait_slice


def _merge_guard_effects(
    state: dict[str, Any],
    result: dict[str, Any] | None,
    removed_ids: Sequence[str],
    guard_logs: Sequence[str],
) -> dict[str, Any]:
    merged = dict(result or {})

    if removed_ids:
        removals = [RemoveMessage(id=message_id) for message_id in removed_ids]
        existing_messages = list(merged.get("messages", []))
        merged["messages"] = removals + existing_messages

    if guard_logs:
        if isinstance(merged.get("logs"), list):
            merged["logs"] = list(merged["logs"]) + list(guard_logs)
        else:
            merged["logs"] = list(state.get("logs", [])) + list(guard_logs)

    return merged


def _execute_node(node_fn: Any, state: dict[str, Any]) -> dict[str, Any]:
    if callable(node_fn):
        return node_fn(state)
    if hasattr(node_fn, "invoke"):
        return node_fn.invoke(state)
    raise TypeError(f"Unsupported node type for guard wrapper: {type(node_fn)!r}")


def _collect_error_text(error: BaseException) -> str:
    texts: list[str] = []
    visited: set[int] = set()
    current: BaseException | None = error

    while current is not None and id(current) not in visited:
        visited.add(id(current))
        texts.append(str(current))
        current = current.__cause__ or current.__context__

    return " | ".join(part for part in texts if part)


def _is_tpm_limit_error(error: BaseException) -> bool:
    text = _collect_error_text(error).lower()
    patterns = (
        "tokens per minute",
        "request too large",
        "rate_limit_exceeded",
        "token limit",
        "413",
    )
    return any(pattern in text for pattern in patterns)


def _extract_provider_tpm_limit(error: BaseException) -> int | None:
    text = _collect_error_text(error)
    match = re.search(r"limit\s+(\d+)", text, flags=re.IGNORECASE)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _remove_ids_for_kept_messages(messages: Sequence[Any], kept_messages: Sequence[Any]) -> list[str]:
    kept_object_ids = {id(message) for message in kept_messages}
    return [
        message.id
        for message in messages
        if getattr(message, "id", None) and id(message) not in kept_object_ids
    ]


def _build_minimal_retry_messages(messages: Sequence[Any]) -> list[Any]:
    if not messages:
        return []

    last_human = next(
        (message for message in reversed(messages) if getattr(message, "type", "") == "human"),
        None,
    )
    if last_human is not None:
        return [last_human]

    return [messages[-1]]


def guard_node(
    node_name: str,
    node_fn: Any,
    model_selector: Callable[[str, dict[str, Any]], str | None],
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def wrapped(state: dict[str, Any]) -> dict[str, Any]:
        messages = list(state.get("messages") or [])
        if not messages:
            return _execute_node(node_fn, state)

        model_name = model_selector(node_name, state)
        if not model_name:
            return _execute_node(node_fn, state)

        kept_messages = messages
        removed_ids: list[str] = []
        guard_logs: list[str] = []

        request_tokens = estimate_messages_tokens(messages)
        decision = project_tpm_pressure(model_name, request_tokens)

        if decision.projected_tokens > _get_soft_tpm_limit(model_name):
            kept_messages, removed_ids = trim_messages_to_budget(
                messages,
                decision.allowed_request_tokens,
            )
            trimmed_tokens = estimate_messages_tokens(kept_messages)

            if len(kept_messages) < len(messages):
                guard_logs.append(
                    f"[TPM Guard] {node_name}: trimmed messages "
                    f"{len(messages)} -> {len(kept_messages)} "
                    f"for model {model_name}."
                )

            request_tokens = trimmed_tokens
            wait_time = wait_for_tpm_budget(model_name, request_tokens)
            if wait_time > 0:
                guard_logs.append(
                    f"[TPM Guard] {node_name}: waited {wait_time:.1f}s "
                    f"for rolling token budget on {model_name}."
                )

        reserve_tokens(model_name, request_tokens)

        guarded_state = dict(state)
        if kept_messages is not messages:
            guarded_state["messages"] = kept_messages

        try:
            result = _execute_node(node_fn, guarded_state)
            return _merge_guard_effects(state, result, removed_ids, guard_logs)
        except Exception as error:
            if not _is_tpm_limit_error(error):
                raise

            provider_limit = _extract_provider_tpm_limit(error)
            if provider_limit:
                learned_limit = _remember_soft_tpm_limit(model_name, provider_limit)
                guard_logs.append(
                    f"[TPM Guard] {node_name}: learned provider TPM limit "
                    f"{provider_limit} for {model_name}; using soft cap {learned_limit}."
                )

            retry_messages = _build_minimal_retry_messages(guarded_state.get("messages") or messages)
            if not retry_messages:
                raise

            retry_removed_ids = _remove_ids_for_kept_messages(messages, retry_messages)
            if len(retry_messages) >= len(messages) and len(retry_removed_ids) == len(removed_ids):
                raise

            guard_logs.append(
                f"[TPM Guard] {node_name}: provider rejected request size; "
                f"cleared message history {len(messages)} -> {len(retry_messages)} and retried."
            )

            retry_tokens = estimate_messages_tokens(retry_messages)
            retry_wait_time = wait_for_tpm_budget(model_name, retry_tokens)
            if retry_wait_time > 0:
                guard_logs.append(
                    f"[TPM Guard] {node_name}: waited {retry_wait_time:.1f}s "
                    f"before retrying on {model_name}."
                )
            reserve_tokens(model_name, retry_tokens)

            retry_state = dict(state)
            retry_state["messages"] = retry_messages
            retry_result = _execute_node(node_fn, retry_state)
            return _merge_guard_effects(state, retry_result, retry_removed_ids, guard_logs)

    wrapped.__name__ = getattr(node_fn, "__name__", f"guarded_{node_name}")
    return wrapped
