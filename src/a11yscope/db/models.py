"""SQLAlchemy ORM models for A11yScope v2."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_new_uuid)
    email = Column(String, unique=True, nullable=False)
    display_name = Column(String, nullable=False, default="")
    role = Column(String, nullable=False, default="auditor")  # admin, auditor, viewer
    password_hash = Column(String, nullable=True)
    must_change_password = Column(Boolean, default=False)
    canvas_api_token_encrypted = Column(Text, nullable=True)
    idp_subject = Column(String, nullable=True)
    idp_provider = Column(String, nullable=True)  # saml, oidc, or NULL
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    last_login_at = Column(DateTime, nullable=True)

    refresh_tokens = relationship("RefreshToken", back_populates="user")


class AppSetting(Base):
    __tablename__ = "app_settings"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=_utcnow)
    updated_by = Column(String, ForeignKey("users.id"), nullable=True)


class AuditLogEntry(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=_utcnow)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    user_email = Column(String, nullable=True)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    detail = Column(Text, nullable=True)  # JSON
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    status = Column(String, default="success")

    __table_args__ = (
        Index("idx_audit_log_timestamp", "timestamp"),
        Index("idx_audit_log_user", "user_id"),
        Index("idx_audit_log_action", "action"),
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(String, primary_key=True, default=_new_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    user = relationship("User", back_populates="refresh_tokens")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, default=_new_uuid)
    user_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    canvas_url = Column(String, nullable=False)
    encrypted_token = Column(LargeBinary, nullable=False)
    token_hint = Column(String(4), nullable=False)
    course_count = Column(Integer, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=_utcnow)


class AuditJob(Base):
    __tablename__ = "audit_jobs"

    id = Column(String, primary_key=True, default=_new_uuid)
    user_id = Column(String, nullable=False, index=True)
    api_key_id = Column(String, ForeignKey("api_keys.id"), nullable=False)
    canvas_url = Column(String, nullable=False)
    course_id = Column(Integer, nullable=False)
    course_name = Column(String, nullable=False)
    status = Column(String, nullable=False, default="queued")
    progress_pct = Column(Integer, nullable=False, default=0)
    current_phase = Column(String, nullable=True)
    current_item = Column(String, nullable=True)
    items_total = Column(Integer, nullable=False, default=0)
    items_checked = Column(Integer, nullable=False, default=0)
    issues_found = Column(Integer, nullable=False, default=0)
    result_json = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    queued_at = Column(DateTime, nullable=False, default=_utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    checkpoint_json = Column(Text, nullable=True)
    queue_position = Column(Integer, nullable=False, default=0)

    items = relationship(
        "AuditJobItem", back_populates="job", cascade="all, delete-orphan"
    )


class AuditJobItem(Base):
    __tablename__ = "audit_job_items"

    id = Column(String, primary_key=True, default=_new_uuid)
    job_id = Column(
        String,
        ForeignKey("audit_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_type = Column(String, nullable=False)
    item_title = Column(String(200), nullable=False)
    status = Column(String, nullable=False, default="pending")
    issues = Column(Integer, nullable=False, default=0)
    checked_at = Column(DateTime, nullable=True)
    sort_order = Column(Integer, nullable=False)

    job = relationship("AuditJob", back_populates="items")
