"""Pydantic schemas for auth requests / responses."""
from __future__ import annotations

from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    must_change_password: bool = False


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class TokenRefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    id: str
    email: str
    display_name: str
    role: str
    must_change_password: bool = False
    is_active: bool = True
    idp_provider: str | None = None
