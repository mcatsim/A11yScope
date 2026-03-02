"""Course listing routes."""
from fastapi import APIRouter, HTTPException

from accessiflow.canvas.client import CanvasClient, CanvasAPIError
from accessiflow.web.session import get_or_create_default_session
from accessiflow.web.models import CourseInfo

router = APIRouter()


@router.get("/courses")
async def list_courses() -> list[CourseInfo]:
    """List the teacher's Canvas courses."""
    session = get_or_create_default_session()
    if not session.validated:
        raise HTTPException(status_code=401, detail="Credentials not configured")

    try:
        async with CanvasClient(session.canvas_base_url, session.canvas_api_token) as client:
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
    return courses
