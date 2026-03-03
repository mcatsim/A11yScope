"""Audit start and status routes."""
import asyncio

from fastapi import APIRouter, Depends, HTTPException

from a11yscope.auth.backend import AuthUser
from a11yscope.auth.dependencies import get_current_user
from a11yscope.audit_log.logger import AuditLogger, get_audit_logger
from a11yscope.audit_log.schemas import AuditAction
from a11yscope.web.session import get_user_session, create_job, get_job, resolve_canvas_token
from a11yscope.web.models import AuditRequest, AuditStatusResponse
from a11yscope.web.audit_runner import run_audit

router = APIRouter()


@router.post("/audit")
async def start_audit(
    req: AuditRequest,
    user: AuthUser = Depends(get_current_user),
    audit: AuditLogger = Depends(get_audit_logger),
) -> dict:
    """Start a new audit job. Returns job_id immediately; runs in background."""
    session = get_user_session(user.id)
    token = resolve_canvas_token(session)
    if not session.validated and not token:
        raise HTTPException(status_code=401, detail="Credentials not configured")

    job = create_job(session, req.course_id)

    await audit.log(
        AuditAction.AUDIT_STARTED,
        user=user,
        resource_type="course",
        resource_id=str(req.course_id),
    )

    async def _progress(msg: dict) -> None:
        job.progress.append(msg)

    async def _run() -> None:
        try:
            await run_audit(
                job=job,
                canvas_base_url=session.canvas_base_url,
                canvas_api_token=token or session.canvas_api_token,
                on_progress=_progress,
            )
        except Exception:
            pass  # Error already captured in job

    asyncio.create_task(_run())

    return {"job_id": job.job_id, "status": job.status}


@router.get("/audit/{job_id}")
async def audit_status(
    job_id: str,
    user: AuthUser = Depends(get_current_user),
) -> AuditStatusResponse:
    """Get audit job status and results."""
    session = get_user_session(user.id)
    job = get_job(session, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    result_data = None
    if job.result:
        result_data = job.result.model_dump(mode="json")

    return AuditStatusResponse(
        job_id=job.job_id,
        status=job.status,
        course_id=job.course_id,
        course_name=job.course_name,
        progress=job.progress,
        result=result_data,
        error=job.error,
    )
