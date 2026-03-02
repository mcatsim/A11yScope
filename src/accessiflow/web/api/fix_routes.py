"""Fix and remediation routes."""
from fastapi import APIRouter, HTTPException

from accessiflow.web.session import get_or_create_default_session, get_job
from accessiflow.web.models import FixRequest, FixResponse
from accessiflow.web.audit_runner import apply_fixes

router = APIRouter()


@router.post("/fix/{job_id}")
async def fix_issues(job_id: str, req: FixRequest) -> FixResponse:
    """Apply auto-fixes to audit results."""
    session = get_or_create_default_session()
    job = get_job(session, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.result:
        raise HTTPException(status_code=400, detail="Audit not complete")

    fixed_count, new_score, errors = await apply_fixes(
        job=job,
        canvas_base_url=session.canvas_base_url,
        canvas_api_token=session.canvas_api_token,
        issue_indices=req.issue_indices or None,
        push_to_canvas=req.push_to_canvas,
    )

    return FixResponse(fixed_count=fixed_count, new_score=new_score, errors=errors)
