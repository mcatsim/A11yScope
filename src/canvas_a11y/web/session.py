"""In-memory session and job store. No database needed."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from canvas_a11y.models import CourseAuditResult


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class AuditJob:
    job_id: str
    course_id: int
    course_name: str = ""
    status: JobStatus = JobStatus.PENDING
    progress: list[dict[str, Any]] = field(default_factory=list)
    result: CourseAuditResult | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class SessionState:
    session_id: str
    canvas_base_url: str = ""
    canvas_api_token: str = ""
    anthropic_api_key: str = ""
    user_name: str = ""
    validated: bool = False
    jobs: dict[str, AuditJob] = field(default_factory=dict)


# Global stores — single-user local tool, no DB needed
_sessions: dict[str, SessionState] = {}


def create_session() -> SessionState:
    sid = uuid.uuid4().hex[:16]
    session = SessionState(session_id=sid)
    _sessions[sid] = session
    return session


def get_session(session_id: str) -> SessionState | None:
    return _sessions.get(session_id)


def get_or_create_default_session() -> SessionState:
    """For single-user mode, return the first session or create one."""
    if _sessions:
        return next(iter(_sessions.values()))
    return create_session()


def create_job(session: SessionState, course_id: int, course_name: str = "") -> AuditJob:
    job_id = uuid.uuid4().hex[:12]
    job = AuditJob(job_id=job_id, course_id=course_id, course_name=course_name)
    session.jobs[job_id] = job
    return job


def get_job(session: SessionState, job_id: str) -> AuditJob | None:
    return session.jobs.get(job_id)
