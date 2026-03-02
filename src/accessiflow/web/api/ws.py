"""WebSocket endpoint for real-time audit progress."""
import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from accessiflow.web.session import get_or_create_default_session, get_job

router = APIRouter()


@router.websocket("/ws/audit/{job_id}")
async def audit_ws(websocket: WebSocket, job_id: str):
    """Stream audit progress messages over WebSocket."""
    await websocket.accept()

    session = get_or_create_default_session()
    job = get_job(session, job_id)

    if not job:
        await websocket.send_json({"type": "error", "message": "Job not found"})
        await websocket.close()
        return

    last_idx = 0
    try:
        while True:
            # Send any new progress messages
            if last_idx < len(job.progress):
                for msg in job.progress[last_idx:]:
                    await websocket.send_json(msg)
                last_idx = len(job.progress)

            # If job is done, send final status and close
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
