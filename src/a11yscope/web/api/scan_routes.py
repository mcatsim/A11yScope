"""Scan management routes -- create, list, cancel, resume scans."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from a11yscope.auth.backend import AuthUser
from a11yscope.auth.dependencies import get_current_user
from a11yscope.audit_log.logger import AuditLogger, get_audit_logger
from a11yscope.audit_log.schemas import AuditAction
from a11yscope.config import get_settings
from a11yscope.crypto import decrypt_token
from a11yscope.db.models import ApiKey
from a11yscope.db.session import get_db, get_session_factory

logger = logging.getLogger(__name__)

router = APIRouter()

# The queue manager instance is set during app startup (see app.py lifespan)
_queue_manager = None


def set_queue_manager(qm):
    global _queue_manager
    _queue_manager = qm


def get_queue_manager():
    if _queue_manager is None:
        raise RuntimeError("Queue manager not initialized")
    return _queue_manager


class CreateScanRequest(BaseModel):
    key_id: str
    course_ids: list[int] = Field(..., min_length=1, max_length=50)

    @field_validator("course_ids")
    @classmethod
    def no_duplicates(cls, v: list[int]) -> list[int]:
        if len(v) != len(set(v)):
            raise ValueError("Duplicate course IDs not allowed")
        return v


class ScanResponse(BaseModel):
    job_id: str
    status: str
    course_id: int
    course_name: str
    progress_pct: int = 0


@router.post("/scans", status_code=201)
async def create_scans(
    req: CreateScanRequest,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> list[ScanResponse]:
    """Queue one or more scans. Returns list of created jobs."""
    # Verify user owns the key
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == req.key_id, ApiKey.user_id == user.id)
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    settings = get_settings()
    qm = get_queue_manager()
    factory = get_session_factory()

    def _decrypt(key_id: str) -> str:
        return decrypt_token(key.encrypted_token, settings.effective_secret_key)

    jobs = []
    for course_id in req.course_ids:
        job_id = await qm.enqueue(
            user_id=user.id,
            api_key_id=req.key_id,
            canvas_url=key.canvas_url,
            course_id=course_id,
            course_name=f"Course {course_id}",  # Will be resolved during scan
            db_session_factory=factory,
            decrypt_fn=_decrypt,
        )
        jobs.append(ScanResponse(
            job_id=job_id, status="queued",
            course_id=course_id, course_name=f"Course {course_id}",
        ))

    await audit.log(
        AuditAction.SCAN_QUEUED, user=user,
        resource_type="scan", resource_id=req.key_id,
        detail={"course_ids": req.course_ids, "count": len(req.course_ids)},
    )

    return jobs


@router.get("/scans")
async def list_scans(
    user: AuthUser = Depends(get_current_user),
) -> list[ScanResponse]:
    """List all scans for the current user."""
    qm = get_queue_manager()
    user_jobs = qm.get_user_jobs(user.id)
    return [
        ScanResponse(
            job_id=j["job_id"], status=j["status"],
            course_id=j["course_id"], course_name=j["course_name"],
            progress_pct=j["progress_pct"],
        )
        for j in user_jobs
        if j is not None
    ]


@router.get("/scans/{job_id}")
async def get_scan(
    job_id: str,
    user: AuthUser = Depends(get_current_user),
) -> dict:
    """Get detailed scan status."""
    qm = get_queue_manager()
    status = qm.get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Scan not found")
    # Verify ownership
    job = qm._jobs.get(job_id)
    if job and job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Scan not found")
    return status


@router.delete("/scans/{job_id}", status_code=204)
async def cancel_scan(
    job_id: str,
    user: AuthUser = Depends(get_current_user),
    audit: AuditLogger = Depends(get_audit_logger),
) -> None:
    """Cancel a queued or running scan."""
    qm = get_queue_manager()
    job = qm._jobs.get(job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Scan not found")
    if not qm.cancel(job_id):
        raise HTTPException(status_code=409, detail="Cannot cancel completed scan")
    await audit.log(
        AuditAction.SCAN_CANCELLED, user=user,
        resource_type="scan", resource_id=job_id,
    )
