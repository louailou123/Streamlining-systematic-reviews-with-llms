"""
LiRA Backend — SSE Events Route
Server-Sent Events endpoint for real-time workflow updates.
"""

import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/events", tags=["Events"])


# In-memory event queues per research_id (replaced by Redis PubSub in Batch 2)
_event_queues: dict[str, list[asyncio.Queue]] = {}


def publish_event(research_id: str, event: dict) -> None:
    """Publish an event to all SSE listeners for a research project."""
    key = str(research_id)
    if key in _event_queues:
        for queue in _event_queues[key]:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass  # Drop if subscriber is too slow


async def _get_user_from_token_param(
    token: str = Query(..., description="JWT access token (required for SSE since EventSource cannot send headers)"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract user from query-param token. Used for SSE where headers aren't possible."""
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


async def _event_generator(research_id: str, request: Request):
    """Async generator that yields SSE events."""
    key = str(research_id)
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)

    if key not in _event_queues:
        _event_queues[key] = []
    _event_queues[key].append(queue)

    try:
        # Send initial connection event
        yield f"event: connected\ndata: {json.dumps({'research_id': key})}\n\n"

        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break

            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                event_type = event.get("event_type", "message")
                data = json.dumps(event)
                yield f"event: {event_type}\ndata: {data}\n\n"
            except asyncio.TimeoutError:
                # Send keepalive ping
                yield f"event: ping\ndata: {json.dumps({'keepalive': True})}\n\n"
    finally:
        # Cleanup
        if key in _event_queues and queue in _event_queues[key]:
            _event_queues[key].remove(queue)
            if not _event_queues[key]:
                del _event_queues[key]


@router.get("/stream/{research_id}")
async def stream_events(
    research_id: UUID,
    request: Request,
    current_user: User = Depends(_get_user_from_token_param),
):
    """SSE endpoint for real-time workflow progress updates."""
    return StreamingResponse(
        _event_generator(str(research_id), request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

