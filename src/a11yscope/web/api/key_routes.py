"""API key management routes.

Canvas API tokens are Fernet-encrypted at rest and never
returned to the client in plaintext (CWE-312).
"""

import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from a11yscope.auth.backend import AuthUser
from a11yscope.auth.dependencies import get_current_user
from a11yscope.audit_log.logger import AuditLogger, get_audit_logger
from a11yscope.audit_log.schemas import AuditAction
from a11yscope.config import get_settings
from a11yscope.crypto import decrypt_token, encrypt_token
from a11yscope.db.models import ApiKey
from a11yscope.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

_SAFE_NAME_RE = re.compile(r"^[\w\s\-\.]+$")


class SaveKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    canvas_url: str = Field(..., min_length=10)
    token: str = Field(..., min_length=20, max_length=200)

    @field_validator("name")
    @classmethod
    def name_safe_chars(cls, v: str) -> str:
        if not _SAFE_NAME_RE.match(v):
            raise ValueError("Name must contain only letters, numbers, spaces, hyphens, dots")
        return v.strip()

    @field_validator("canvas_url")
    @classmethod
    def url_must_be_https(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError("Canvas URL must use HTTPS")
        return v.rstrip("/")


class KeyResponse(BaseModel):
    id: str
    name: str
    canvas_url: str
    token_hint: str
    course_count: int | None
    last_used_at: str | None
    created_at: str


@router.post("/keys", status_code=201)
async def create_key(
    req: SaveKeyRequest,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> KeyResponse:
    """Save an encrypted Canvas API key."""
    settings = get_settings()
    encrypted = encrypt_token(req.token, settings.effective_secret_key)
    hint = req.token[-4:]

    key = ApiKey(
        user_id=user.id,
        name=req.name,
        canvas_url=req.canvas_url,
        encrypted_token=encrypted,
        token_hint=hint,
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)

    await audit.log(
        AuditAction.KEY_CREATED, user=user,
        resource_type="api_key", resource_id=key.id,
        detail={"name": req.name, "canvas_url": req.canvas_url},
    )

    return KeyResponse(
        id=key.id, name=key.name, canvas_url=key.canvas_url,
        token_hint=hint, course_count=key.course_count,
        last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
        created_at=key.created_at.isoformat(),
    )


@router.get("/keys")
async def list_keys(
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[KeyResponse]:
    """List the current user's saved API keys (tokens masked)."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == user.id).order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()
    return [
        KeyResponse(
            id=k.id, name=k.name, canvas_url=k.canvas_url,
            token_hint=k.token_hint, course_count=k.course_count,
            last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
            created_at=k.created_at.isoformat(),
        )
        for k in keys
    ]


@router.delete("/keys/{key_id}", status_code=204)
async def delete_key(
    key_id: str,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> None:
    """Delete a saved API key. User-scoped."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id)
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    await db.delete(key)
    await db.commit()
    await audit.log(
        AuditAction.KEY_DELETED, user=user,
        resource_type="api_key", resource_id=key_id,
    )


@router.get("/keys/{key_id}/courses")
async def list_courses_for_key(
    key_id: str,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Fetch available courses for a saved API key."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id)
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")

    settings = get_settings()
    token = decrypt_token(key.encrypted_token, settings.effective_secret_key)

    from a11yscope.canvas.client import CanvasClient
    async with CanvasClient(key.canvas_url, token) as client:
        courses = await client.get_courses()

    # Update cached course count
    key.course_count = len(courses)
    key.last_used_at = datetime.now(timezone.utc)
    await db.commit()

    return [
        {"id": c["id"], "name": c["name"], "code": c.get("course_code", "")}
        for c in courses
    ]
