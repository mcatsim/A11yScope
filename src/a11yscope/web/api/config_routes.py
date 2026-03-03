"""Configuration and credential validation routes."""
from fastapi import APIRouter, Depends

from a11yscope.auth.backend import AuthUser
from a11yscope.auth.dependencies import get_current_user
from a11yscope.audit_log.logger import AuditLogger, get_audit_logger
from a11yscope.audit_log.schemas import AuditAction
from a11yscope.canvas.client import CanvasClient, CanvasAPIError
from a11yscope.web.session import get_user_session, resolve_canvas_token
from a11yscope.web.models import ConfigRequest, ConfigStatus

router = APIRouter()


@router.post("/config")
async def set_config(
    req: ConfigRequest,
    user: AuthUser = Depends(get_current_user),
    audit: AuditLogger = Depends(get_audit_logger),
) -> dict:
    """Validate credentials by calling Canvas /users/self."""
    session = get_user_session(user.id)

    try:
        async with CanvasClient(req.canvas_base_url, req.canvas_api_token) as client:
            canvas_user = await client.get("users/self")
            user_name = canvas_user.get("name", canvas_user.get("short_name", "Unknown"))
    except CanvasAPIError as e:
        await audit.log(AuditAction.CONFIG_VALIDATED, user=user, status="failure", detail={"error": str(e)})
        return {"ok": False, "error": f"Canvas API error {e.status_code}: {e.message}"}
    except Exception as e:
        await audit.log(AuditAction.CONFIG_VALIDATED, user=user, status="failure", detail={"error": str(e)})
        return {"ok": False, "error": f"Connection failed: {e}"}

    session.canvas_base_url = req.canvas_base_url
    session.canvas_api_token = req.canvas_api_token
    session.user_name = user_name
    session.validated = True

    await audit.log(AuditAction.CONFIG_VALIDATED, user=user, detail={"canvas_url": req.canvas_base_url})
    return {"ok": True, "user_name": user_name}


@router.get("/config/status")
async def config_status(
    user: AuthUser = Depends(get_current_user),
) -> ConfigStatus:
    """Check if session has valid credentials."""
    session = get_user_session(user.id)
    return ConfigStatus(
        validated=session.validated,
        user_name=session.user_name,
        canvas_base_url=session.canvas_base_url,
    )
