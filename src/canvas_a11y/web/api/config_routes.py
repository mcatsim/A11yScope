"""Configuration and credential validation routes."""
from fastapi import APIRouter

from canvas_a11y.canvas.client import CanvasClient, CanvasAPIError
from canvas_a11y.web.session import get_or_create_default_session
from canvas_a11y.web.models import ConfigRequest, ConfigStatus

router = APIRouter()


@router.post("/config")
async def set_config(req: ConfigRequest) -> dict:
    """Validate credentials by calling Canvas /users/self."""
    session = get_or_create_default_session()

    # Validate Canvas credentials
    try:
        async with CanvasClient(req.canvas_base_url, req.canvas_api_token) as client:
            user = await client.get("users/self")
            user_name = user.get("name", user.get("short_name", "Unknown"))
    except CanvasAPIError as e:
        return {"ok": False, "error": f"Canvas API error {e.status_code}: {e.message}"}
    except Exception as e:
        return {"ok": False, "error": f"Connection failed: {e}"}

    session.canvas_base_url = req.canvas_base_url
    session.canvas_api_token = req.canvas_api_token
    session.anthropic_api_key = req.anthropic_api_key
    session.user_name = user_name
    session.validated = True

    return {"ok": True, "user_name": user_name}


@router.get("/config/status")
async def config_status() -> ConfigStatus:
    """Check if session has valid credentials."""
    session = get_or_create_default_session()
    return ConfigStatus(
        validated=session.validated,
        user_name=session.user_name,
        canvas_base_url=session.canvas_base_url,
        has_anthropic_key=bool(session.anthropic_api_key),
    )
