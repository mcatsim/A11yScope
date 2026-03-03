"""WebSocket endpoint for real-time audit progress."""
import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from a11yscope.auth.jwt import decode_access_token
from a11yscope.config import get_settings
from a11yscope.web.session import get_user_session, get_job

router = APIRouter()


@router.websocket("/ws/audit/{job_id}")
async def audit_ws(websocket: WebSocket, job_id: str, token: str | None = None):
    """Stream audit progress messages over WebSocket.

    For auth_mode != none, pass ?token=<jwt> as query param.
    """
    await websocket.accept()

    settings = get_settings()
    user_id = "anonymous"

    if settings.auth_mode != "none":
        if not token:
            await websocket.send_json({"type": "error", "message": "Authentication required"})
            await websocket.close(code=4001)
            return
        payload = decode_access_token(token)
        if payload is None:
            await websocket.send_json({"type": "error", "message": "Invalid token"})
            await websocket.close(code=4001)
            return
        user_id = payload["sub"]

    session = get_user_session(user_id)
    job = get_job(session, job_id)

    if not job:
        await websocket.send_json({"type": "error", "message": "Job not found"})
        await websocket.close()
        return

    last_idx = 0
    try:
        while True:
            if last_idx < len(job.progress):
                for msg in job.progress[last_idx:]:
                    await websocket.send_json(msg)
                last_idx = len(job.progress)

            if job.status in ("complete", "failed"):
                break

            await asyncio.sleep(0.3)

    except WebSocketDisconnect:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
