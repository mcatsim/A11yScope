"""Fix and remediation routes."""
from fastapi import APIRouter, Depends, HTTPException

from a11yscope.auth.backend import AuthUser
from a11yscope.auth.dependencies import require_role
from a11yscope.audit_log.logger import AuditLogger, get_audit_logger
from a11yscope.audit_log.schemas import AuditAction
from a11yscope.web.session import get_user_session, get_job, resolve_canvas_token
from a11yscope.web.models import FixRequest, FixResponse
from a11yscope.web.audit_runner import apply_fixes

router = APIRouter()


@router.post("/fix/{job_id}")
async def fix_issues(
    job_id: str,
    req: FixRequest,
    user: AuthUser = Depends(require_role("admin", "auditor")),
    audit: AuditLogger = Depends(get_audit_logger),
) -> FixResponse:
    """Apply auto-fixes to audit results."""
    session = get_user_session(user.id)
    job = get_job(session, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.result:
        raise HTTPException(status_code=400, detail="Audit not complete")

    token = resolve_canvas_token(session)
    fixed_count, new_score, errors = await apply_fixes(
        job=job,
        canvas_base_url=session.canvas_base_url,
        canvas_api_token=token or session.canvas_api_token,
        issue_indices=req.issue_indices or None,
        push_to_canvas=req.push_to_canvas,
    )

    await audit.log(
        AuditAction.FIX_APPLIED,
        user=user,
        resource_type="course",
        resource_id=str(job.course_id),
        detail={"fixed_count": fixed_count, "push_to_canvas": req.push_to_canvas},
    )

    return FixResponse(fixed_count=fixed_count, new_score=new_score, errors=errors)
