"""Pydantic schemas for web API requests and responses."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ConfigRequest(BaseModel):
    canvas_base_url: str = "https://canvas.jccc.edu"
    canvas_api_token: str


class ConfigStatus(BaseModel):
    validated: bool
    user_name: str = ""
    canvas_base_url: str = ""


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


class AIConfigRequest(BaseModel):
    provider: str
    api_key: str
    model: str = ""


class AIConfigStatus(BaseModel):
    configured: bool = False
    provider: str = ""
    model: str = ""
    validated: bool = False


class AISuggestionRequest(BaseModel):
    issue_index: int = 0


class AISuggestionResponse(BaseModel):
    check_id: str = ""
    explanation: str = ""
    suggested_fix: str = ""
    provider: str = ""
    model: str = ""
    error: Optional[str] = None
