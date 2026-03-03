"""WebSocket endpoint for scan progress streaming.

Auth is via first message (not URL query param) to prevent
token leakage in server logs (CWE-598).
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from a11yscope.auth.jwt import decode_access_token
from a11yscope.config import get_settings
from a11yscope.web.api.scan_routes import get_queue_manager

logger = logging.getLogger(__name__)

router = APIRouter()

_AUTH_TIMEOUT_SECONDS = 5


@router.websocket("/ws/scan/{job_id}")
async def scan_ws(websocket: WebSocket, job_id: str):
    """Stream scan progress over WebSocket with first-message auth.

    Protocol:
    1. Client connects to /ws/scan/{job_id}
    2. Server accepts the connection
    3. If auth_mode != "none", client must send:
       {"type": "auth", "token": "<JWT>"}
       within _AUTH_TIMEOUT_SECONDS
    4. Server replays any existing progress_log entries (reconnection support)
    5. Server streams new progress messages as they appear
    6. Connection closes when job reaches terminal state
    """
    await websocket.accept()

    settings = get_settings()
    user_id = "anonymous"

    # --- Auth phase ---
    if settings.auth_mode != "none":
        try:
            msg = await asyncio.wait_for(
                websocket.receive_json(),
                timeout=_AUTH_TIMEOUT_SECONDS,
            )
        except (asyncio.TimeoutError, Exception):
            await websocket.send_json({"type": "error", "message": "Auth timeout"})
            await websocket.close(code=4001)
            return

        if msg.get("type") != "auth" or not msg.get("token"):
            await websocket.send_json(
                {"type": "error", "message": "Expected auth message"}
            )
            await websocket.close(code=4001)
            return

        payload = decode_access_token(msg["token"])
        if payload is None:
            await websocket.send_json(
                {"type": "error", "message": "Invalid token"}
            )
            await websocket.close(code=4001)
            return

        user_id = payload["sub"]

    # --- Resolve job ---
    qm = get_queue_manager()
    job = qm._jobs.get(job_id)
    if not job:
        await websocket.send_json(
            {"type": "error", "message": "Job not found"}
        )
        await websocket.close()
        return

    # Verify ownership
    if settings.auth_mode != "none" and job.user_id != user_id:
        await websocket.send_json(
            {"type": "error", "message": "Access denied"}
        )
        await websocket.close(code=4003)
        return

    # --- Replay existing progress (for reconnection) ---
    for entry in job.progress_log:
        await websocket.send_json(entry)

    # --- Stream new progress ---
    last_idx = len(job.progress_log)
    try:
        while True:
            if last_idx < len(job.progress_log):
                for entry in job.progress_log[last_idx:]:
                    await websocket.send_json(entry)
                last_idx = len(job.progress_log)

            if job.status in ("complete", "failed", "cancelled"):
                break

            await asyncio.sleep(0.3)
    except WebSocketDisconnect:
        logger.debug("WebSocket disconnected for job %s", job_id)
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
