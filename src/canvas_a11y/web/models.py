"""Pydantic schemas for web API requests and responses."""
from __future__ import annotations

from pydantic import BaseModel


class ConfigRequest(BaseModel):
    canvas_base_url: str = "https://canvas.jccc.edu"
    canvas_api_token: str
    anthropic_api_key: str = ""


class ConfigStatus(BaseModel):
    validated: bool
    user_name: str = ""
    canvas_base_url: str = ""
    has_anthropic_key: bool = False


class CourseInfo(BaseModel):
    id: int
    name: str
    course_code: str = ""
    term: str = ""


class AuditRequest(BaseModel):
    course_id: int


class AuditStatusResponse(BaseModel):
    job_id: str
    status: str
    course_id: int
    course_name: str = ""
    progress: list[dict] = []
    result: dict | None = None
    error: str | None = None


class FixRequest(BaseModel):
    issue_indices: list[int] = []
    push_to_canvas: bool = False


class FixResponse(BaseModel):
    fixed_count: int
    new_score: float | None = None
    errors: list[str] = []
