"""Audit log action enum and Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class AuditAction(StrEnum):
    # Auth
    LOGIN = "login"
    LOGIN_FAILED = "login.failed"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token.refresh"
    PASSWORD_CHANGED = "password.changed"

    # Canvas config
    CONFIG_VALIDATED = "config.validated"
    CONFIG_STATUS = "config.status"

    # Courses
    COURSES_LISTED = "courses.listed"

    # Audit
    AUDIT_STARTED = "audit.started"
    AUDIT_COMPLETED = "audit.completed"

    # Fix
    FIX_APPLIED = "fix.applied"

    # Reports
    REPORT_DOWNLOADED = "report.downloaded"

    # AI
    AI_CONFIG_CHANGED = "ai.config_changed"
    AI_SUGGESTION = "ai.suggestion"

    # Standards
    STANDARDS_UPDATED = "standards.updated"
    STANDARDS_RESET = "standards.reset"

    # Admin
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    SETTING_UPDATED = "setting.updated"
    SSO_CONFIG_UPDATED = "sso.config_updated"


class AuditLogQuery(BaseModel):
    action: str | None = None
    user_id: str | None = None
    resource_type: str | None = None
    status: str | None = None
    after: datetime | None = None
    before: datetime | None = None
    limit: int = 100
    offset: int = 0


class AuditLogResponse(BaseModel):
    id: int
    timestamp: datetime | None = None
    user_id: str | None = None
    user_email: str | None = None
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    detail: str | None = None
    ip_address: str | None = None
    status: str = "success"
