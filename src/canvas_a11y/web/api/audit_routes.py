"""Audit start and status routes."""
import asyncio

from fastapi import APIRouter, HTTPException

from canvas_a11y.web.session import get_or_create_default_session, create_job, get_job
from canvas_a11y.web.models import AuditRequest, AuditStatusResponse
from canvas_a11y.web.audit_runner import run_audit

router = APIRouter()


@router.post("/audit")
async def start_audit(req: AuditRequest) -> dict:
    """Start a new audit job. Returns job_id immediately; runs in background."""
    session = get_or_create_default_session()
    if not session.validated:
        raise HTTPException(status_code=401, detail="Credentials not configured")

    job = create_job(session, req.course_id)

    async def _progress(msg: dict) -> None:
        job.progress.append(msg)

    async def _run() -> None:
        try:
            await run_audit(
                job=job,
                canvas_base_url=session.canvas_base_url,
                canvas_api_token=session.canvas_api_token,
                on_progress=_progress,
            )
        except Exception:
            pass  # Error already captured in job

    asyncio.create_task(_run())

    return {"job_id": job.job_id, "status": job.status}


@router.get("/audit/{job_id}")
async def audit_status(job_id: str) -> AuditStatusResponse:
    """Get audit job status and results."""
    session = get_or_create_default_session()
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
