"""Admin routes — user CRUD, settings, SSO config, audit logs."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from a11yscope.auth.backend import AuthUser
from a11yscope.auth.dependencies import require_role
from a11yscope.auth.password import hash_password
from a11yscope.audit_log.logger import AuditLogger, get_audit_logger
from a11yscope.audit_log.schemas import AuditAction, AuditLogResponse
from a11yscope.db.models import AppSetting, AuditLogEntry, User
from a11yscope.db.session import get_db

router = APIRouter(tags=["admin"])


# ── Schemas ─────────────────────────────────────────────────────


class CreateUserRequest(BaseModel):
    email: str
    display_name: str = ""
    role: str = "auditor"
    password: str | None = None


class UpdateUserRequest(BaseModel):
    display_name: str | None = None
    role: str | None = None
    is_active: bool | None = None
    password: str | None = None


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    role: str
    is_active: bool
    idp_provider: str | None = None
    must_change_password: bool = False
    created_at: datetime | None = None
    last_login_at: datetime | None = None


class SettingResponse(BaseModel):
    key: str
    value: str
    updated_at: datetime | None = None


class SetSettingRequest(BaseModel):
    key: str
    value: str


# ── User Management ────────────────────────────────────────────


@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    user: AuthUser = Depends(require_role("admin")),
) -> list[UserResponse]:
    """List all users."""
    result = await db.execute(select(User).order_by(User.created_at))
    users = result.scalars().all()
    return [
        UserResponse(
            id=u.id,
            email=u.email,
            display_name=u.display_name,
            role=u.role,
            is_active=u.is_active,
            idp_provider=u.idp_provider,
            must_change_password=u.must_change_password,
            created_at=u.created_at,
            last_login_at=u.last_login_at,
        )
        for u in users
    ]


@router.post("/users")
async def create_user(
    req: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    user: AuthUser = Depends(require_role("admin")),
    audit: AuditLogger = Depends(get_audit_logger),
) -> UserResponse:
    """Create a new user."""
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already exists")

    if req.role not in ("admin", "auditor", "viewer"):
        raise HTTPException(status_code=400, detail="Invalid role")

    new_user = User(
        email=req.email,
        display_name=req.display_name or req.email.split("@")[0],
        role=req.role,
        password_hash=hash_password(req.password) if req.password else None,
        must_change_password=bool(req.password),
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    await audit.log(
        AuditAction.USER_CREATED,
        user=user,
        resource_type="user",
        resource_id=new_user.id,
        detail={"email": req.email, "role": req.role},
    )

    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        display_name=new_user.display_name,
        role=new_user.role,
        is_active=new_user.is_active,
        must_change_password=new_user.must_change_password,
        created_at=new_user.created_at,
    )


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    req: UpdateUserRequest,
    db: AsyncSession = Depends(get_db),
    user: AuthUser = Depends(require_role("admin")),
    audit: AuditLogger = Depends(get_audit_logger),
) -> UserResponse:
    """Update a user."""
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    changes = {}
    if req.display_name is not None:
        target.display_name = req.display_name
        changes["display_name"] = req.display_name
    if req.role is not None:
        if req.role not in ("admin", "auditor", "viewer"):
            raise HTTPException(status_code=400, detail="Invalid role")
        target.role = req.role
        changes["role"] = req.role
    if req.is_active is not None:
        target.is_active = req.is_active
        changes["is_active"] = req.is_active
    if req.password is not None:
        target.password_hash = hash_password(req.password)
        target.must_change_password = True
        changes["password_reset"] = True

    await db.commit()
    await db.refresh(target)

    await audit.log(
        AuditAction.USER_UPDATED,
        user=user,
        resource_type="user",
        resource_id=user_id,
        detail=changes,
    )

    return UserResponse(
        id=target.id,
        email=target.email,
        display_name=target.display_name,
        role=target.role,
        is_active=target.is_active,
        idp_provider=target.idp_provider,
        must_change_password=target.must_change_password,
        created_at=target.created_at,
        last_login_at=target.last_login_at,
    )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: AuthUser = Depends(require_role("admin")),
    audit: AuditLogger = Depends(get_audit_logger),
):
    """Deactivate (soft-delete) a user."""
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    target.is_active = False
    await db.commit()

    await audit.log(
        AuditAction.USER_DELETED,
        user=user,
        resource_type="user",
        resource_id=user_id,
        detail={"email": target.email},
    )
    return {"ok": True}


# ── Settings ───────────────────────────────────────────────────


@router.get("/settings")
async def list_settings(
    db: AsyncSession = Depends(get_db),
    user: AuthUser = Depends(require_role("admin")),
) -> list[SettingResponse]:
    """List all app settings."""
    result = await db.execute(select(AppSetting).order_by(AppSetting.key))
    return [
        SettingResponse(key=s.key, value=s.value, updated_at=s.updated_at)
        for s in result.scalars().all()
    ]


@router.put("/settings")
async def set_setting(
    req: SetSettingRequest,
    db: AsyncSession = Depends(get_db),
    user: AuthUser = Depends(require_role("admin")),
    audit: AuditLogger = Depends(get_audit_logger),
) -> SettingResponse:
    """Set an app setting (upsert)."""
    result = await db.execute(select(AppSetting).where(AppSetting.key == req.key))
    setting = result.scalar_one_or_none()

    if setting:
        setting.value = req.value
        setting.updated_by = user.id
    else:
        setting = AppSetting(key=req.key, value=req.value, updated_by=user.id)
        db.add(setting)

    await db.commit()
    await db.refresh(setting)

    await audit.log(
        AuditAction.SETTING_UPDATED,
        user=user,
        resource_type="config",
        resource_id=req.key,
        detail={"value": req.value},
    )

    return SettingResponse(key=setting.key, value=setting.value, updated_at=setting.updated_at)


# ── Audit Logs ─────────────────────────────────────────────────


@router.get("/audit-logs")
async def get_audit_logs(
    action: str | None = None,
    user_id: str | None = None,
    resource_type: str | None = None,
    status: str | None = None,
    after: datetime | None = None,
    before: datetime | None = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: AuthUser = Depends(require_role("admin")),
) -> dict:
    """Query audit logs with filters."""
    query = select(AuditLogEntry).order_by(AuditLogEntry.timestamp.desc())

    if action:
        query = query.where(AuditLogEntry.action == action)
    if user_id:
        query = query.where(AuditLogEntry.user_id == user_id)
    if resource_type:
        query = query.where(AuditLogEntry.resource_type == resource_type)
    if status:
        query = query.where(AuditLogEntry.status == status)
    if after:
        query = query.where(AuditLogEntry.timestamp >= after)
    if before:
        query = query.where(AuditLogEntry.timestamp <= before)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Page
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    entries = result.scalars().all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "entries": [
            AuditLogResponse(
                id=e.id,
                timestamp=e.timestamp,
                user_id=e.user_id,
                user_email=e.user_email,
                action=e.action,
                resource_type=e.resource_type,
                resource_id=e.resource_id,
                detail=e.detail,
                ip_address=e.ip_address,
                status=e.status,
            ).model_dump()
            for e in entries
        ],
    }
