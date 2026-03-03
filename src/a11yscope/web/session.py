"""In-memory session and job store — user-keyed for v2."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from a11yscope.models import CourseAuditResult


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class AuditJob:
    job_id: str
    course_id: int
    user_id: str = "anonymous"
    course_name: str = ""
    status: JobStatus = JobStatus.PENDING
    progress: list[dict[str, Any]] = field(default_factory=list)
    result: CourseAuditResult | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class SessionState:
    session_id: str
    user_id: str = "anonymous"
    canvas_base_url: str = ""
    canvas_api_token: str = ""
    user_name: str = ""
    validated: bool = False
    # AI configuration
    ai_provider: str = ""
    ai_api_key: str = ""
    ai_model: str = ""
    ai_validated: bool = False
    jobs: dict[str, AuditJob] = field(default_factory=dict)


# Global stores — keyed by user_id
_sessions: dict[str, SessionState] = {}


def create_session(user_id: str = "anonymous") -> SessionState:
    sid = uuid.uuid4().hex[:16]
    session = SessionState(session_id=sid, user_id=user_id)
    _sessions[user_id] = session
    return session


def get_session(session_id: str) -> SessionState | None:
    # Legacy lookup by session_id
    for s in _sessions.values():
        if s.session_id == session_id:
            return s
    return None


def get_or_create_default_session() -> SessionState:
    """For single-user mode, return the first session or create one."""
    if _sessions:
        return next(iter(_sessions.values()))
    return create_session()


def get_user_session(user_id: str) -> SessionState:
    """Get or create a session for a specific user."""
    if user_id in _sessions:
        return _sessions[user_id]
    return create_session(user_id)


def resolve_canvas_token(session: SessionState) -> str:
    """Resolve Canvas API token: per-user session → shared env → config."""
    if session.canvas_api_token:
        return session.canvas_api_token

    from a11yscope.config import get_settings
    settings = get_settings()

    if settings.shared_canvas_token:
        return settings.shared_canvas_token
    if settings.canvas_api_token:
        return settings.canvas_api_token
    return ""


def create_job(session: SessionState, course_id: int, course_name: str = "") -> AuditJob:
    job_id = uuid.uuid4().hex[:12]
    job = AuditJob(job_id=job_id, course_id=course_id, user_id=session.user_id, course_name=course_name)
    session.jobs[job_id] = job
    return job


def get_job(session: SessionState, job_id: str) -> AuditJob | None:
    return session.jobs.get(job_id)
