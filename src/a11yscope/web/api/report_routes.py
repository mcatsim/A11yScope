"""Report download routes."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from a11yscope.auth.backend import AuthUser
from a11yscope.auth.dependencies import get_current_user
from a11yscope.audit_log.logger import AuditLogger, get_audit_logger
from a11yscope.audit_log.schemas import AuditAction
from a11yscope.reporting.html_report import generate_html_report
from a11yscope.reporting.json_report import generate_json_report
from a11yscope.reporting.vpat_report import generate_vpat_report
from a11yscope.web.session import get_user_session, get_job

router = APIRouter()
OUTPUT_DIR = Path("output/web_reports")


@router.get("/report/{job_id}/html")
async def download_html_report(
    job_id: str,
    user: AuthUser = Depends(get_current_user),
    audit: AuditLogger = Depends(get_audit_logger),
):
    """Generate and download the HTML report."""
    session = get_user_session(user.id)
    job = get_job(session, job_id)
    if not job or not job.result:
        raise HTTPException(status_code=404, detail="Audit result not found")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"audit_{job.course_id}_{job_id}.html"
    generate_html_report(job.result, out_path)

    await audit.log(
        AuditAction.REPORT_DOWNLOADED,
        user=user,
        resource_type="report",
        resource_id=job_id,
        detail={"format": "html", "course_id": job.course_id},
    )

    return FileResponse(
        str(out_path),
        media_type="text/html",
        filename=f"a11y_audit_{job.course_id}.html",
    )


@router.get("/report/{job_id}/json")
async def download_json_report(
    job_id: str,
    user: AuthUser = Depends(get_current_user),
    audit: AuditLogger = Depends(get_audit_logger),
):
    """Generate and download the JSON report."""
    session = get_user_session(user.id)
    job = get_job(session, job_id)
    if not job or not job.result:
        raise HTTPException(status_code=404, detail="Audit result not found")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"audit_{job.course_id}_{job_id}.json"
    generate_json_report(job.result, out_path)

    await audit.log(
        AuditAction.REPORT_DOWNLOADED,
        user=user,
        resource_type="report",
        resource_id=job_id,
        detail={"format": "json", "course_id": job.course_id},
    )

    return FileResponse(
        str(out_path),
        media_type="application/json",
        filename=f"a11y_audit_{job.course_id}.json",
    )


@router.get("/report/{job_id}/vpat")
async def download_vpat_report(
    job_id: str,
    user: AuthUser = Depends(get_current_user),
    audit: AuditLogger = Depends(get_audit_logger),
):
    session = get_user_session(user.id)
    job = get_job(session, job_id)
    if not job or not job.result:
        raise HTTPException(status_code=404, detail="Audit result not found")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"vpat_{job.course_id}_{job_id}.html"
    generate_vpat_report(job.result, out_path)

    await audit.log(
        AuditAction.REPORT_DOWNLOADED,
        user=user,
        resource_type="report",
        resource_id=job_id,
        detail={"format": "vpat", "course_id": job.course_id},
    )

    return FileResponse(
        str(out_path),
        media_type="text/html",
        filename=f"vpat_{job.course_id}.html",
    )
