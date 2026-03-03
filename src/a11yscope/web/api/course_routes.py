"""Course listing routes."""
from fastapi import APIRouter, Depends, HTTPException

from a11yscope.auth.backend import AuthUser
from a11yscope.auth.dependencies import get_current_user
from a11yscope.audit_log.logger import AuditLogger, get_audit_logger
from a11yscope.audit_log.schemas import AuditAction
from a11yscope.canvas.client import CanvasClient, CanvasAPIError
from a11yscope.web.session import get_user_session, resolve_canvas_token
from a11yscope.web.models import CourseInfo

router = APIRouter()


@router.get("/courses")
async def list_courses(
    user: AuthUser = Depends(get_current_user),
    audit: AuditLogger = Depends(get_audit_logger),
) -> list[CourseInfo]:
    """List the teacher's Canvas courses."""
    session = get_user_session(user.id)
    token = resolve_canvas_token(session)
    if not session.validated and not token:
        raise HTTPException(status_code=401, detail="Credentials not configured")

    base_url = session.canvas_base_url or "https://canvas.jccc.edu"

    try:
        async with CanvasClient(base_url, token or session.canvas_api_token) as client:
            raw = await client.get_courses()
    except CanvasAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    courses = []
    for c in raw:
        courses.append(CourseInfo(
            id=c["id"],
            name=c.get("name", "Unknown"),
            course_code=c.get("course_code", ""),
            term=c.get("term", {}).get("name", "") if isinstance(c.get("term"), dict) else "",
        ))

    await audit.log(AuditAction.COURSES_LISTED, user=user, detail={"count": len(courses)})
    return courses
