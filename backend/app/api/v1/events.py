"""
LiRA Backend — WebSocket Events Route
WebSocket endpoint for real-time workflow updates.
Replaces the previous SSE (Server-Sent Events) implementation with
full-duplex WebSocket for bidirectional communication.
"""

import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.security import decode_token
from app.db.session import AsyncSessionLocal
from app.models.user import User

router = APIRouter(prefix="/events", tags=["Events"])


# ── Connection Manager ────────────────────────────────────────

class ConnectionManager:
    """
    Manages active WebSocket connections per research_id.
    Each research project can have multiple concurrent subscribers.
    """

    def __init__(self):
        # research_id -> list of (WebSocket, asyncio.Queue) pairs
        self._subscribers: dict[str, list[tuple[WebSocket, asyncio.Queue]]] = {}

    def subscribe(self, research_id: str, websocket: WebSocket) -> asyncio.Queue:
        """Register a new subscriber and return its event queue."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=500)
        if research_id not in self._subscribers:
            self._subscribers[research_id] = []
        self._subscribers[research_id].append((websocket, queue))
        return queue

    def unsubscribe(self, research_id: str, websocket: WebSocket) -> None:
        """Remove a subscriber."""
        if research_id in self._subscribers:
            self._subscribers[research_id] = [
                (ws, q) for ws, q in self._subscribers[research_id] if ws is not websocket
            ]
            if not self._subscribers[research_id]:
                del self._subscribers[research_id]

    def publish(self, research_id: str, event: dict) -> None:
        """Push an event to all subscribers for a research project."""
        if research_id in self._subscribers:
            for _, queue in self._subscribers[research_id]:
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    pass  # Drop if subscriber is too slow


# Singleton manager
_manager = ConnectionManager()


def publish_event(research_id: str, event: dict) -> None:
    """
    Publish an event to all WebSocket listeners for a research project.
    This is the public API consumed by EventService — the function signature
    is identical to the previous SSE implementation so no callers need to change.
    """
    _manager.publish(str(research_id), event)


# ── WebSocket Authentication ──────────────────────────────────

async def _authenticate_websocket(token: str) -> User | None:
    """Validate a JWT token and return the User, or None if invalid."""
    try:
        payload = decode_token(token)
    except Exception:
        return None

    if not payload or payload.get("type") != "access":
        return None

    user_id_str = payload.get("sub")
    if not user_id_str:
        return None

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        return None

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user or not user.is_active:
                return None
            return user
    except Exception:
        return None


# ── WebSocket Endpoint ────────────────────────────────────────

@router.websocket("/ws/{research_id}")
async def websocket_events(websocket: WebSocket, research_id: UUID):
    """
    WebSocket endpoint for real-time workflow progress updates.

    Protocol:
      1. Server accepts the connection immediately.
      2. Client MUST send an auth message as its first message:
         {"type": "auth", "token": "<JWT access token>"}
      3. On success, server sends: {"type": "auth_ok"}
      4. On failure, server sends: {"type": "auth_error", "message": "..."}
         and closes the connection.
      5. After auth, server pushes workflow events as JSON objects.
      6. Server sends periodic keepalive pings every 25 seconds.
    """
    await websocket.accept()

    key = str(research_id)

    # ── Step 1: Authenticate ──────────────────────────────
    try:
        # Wait up to 10 seconds for the auth message
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
        auth_msg = json.loads(raw)
    except (asyncio.TimeoutError, json.JSONDecodeError, WebSocketDisconnect):
        try:
            await websocket.send_json({"type": "auth_error", "message": "Auth timeout or invalid message"})
            await websocket.close(code=4001, reason="Auth failed")
        except Exception:
            pass
        return

    if auth_msg.get("type") != "auth" or not auth_msg.get("token"):
        try:
            await websocket.send_json({"type": "auth_error", "message": "Expected auth message with token"})
            await websocket.close(code=4001, reason="Auth failed")
        except Exception:
            pass
        return

    user = await _authenticate_websocket(auth_msg["token"])
    if not user:
        try:
            await websocket.send_json({"type": "auth_error", "message": "Invalid or expired token"})
            await websocket.close(code=4002, reason="Invalid token")
        except Exception:
            pass
        return

    # Auth success
    await websocket.send_json({"type": "auth_ok", "research_id": key})

    # ── Step 2: Subscribe and fan out events ──────────────
    queue = _manager.subscribe(key, websocket)

    # Send initial connected event
    await websocket.send_json({"type": "connected", "research_id": key})

    async def _send_events():
        """Read from queue and send to client."""
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=25.0)
                await websocket.send_json(event)
            except asyncio.TimeoutError:
                # Keepalive ping
                await websocket.send_json({"type": "ping"})

    async def _receive_messages():
        """Read from client to detect disconnects.
        Also handles future bidirectional commands."""
        while True:
            msg = await websocket.receive_text()
            # Future: handle client commands here (e.g., subscribe to different research_id)
            # For now, we just need to read to detect disconnects

    try:
        # Run both tasks concurrently — when either ends, the connection is done
        await asyncio.gather(_send_events(), _receive_messages())
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        _manager.unsubscribe(key, websocket)
