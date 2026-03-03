"""FastAPI dependencies for auth: get_current_user, require_role."""
from __future__ import annotations

from functools import lru_cache

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from a11yscope.auth.backend import ANONYMOUS_USER, AuthUser
from a11yscope.auth.jwt import decode_access_token
from a11yscope.config import get_settings
from a11yscope.db.session import get_db


@lru_cache
def _auth_mode() -> str:
    return get_settings().auth_mode


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AuthUser:
    """Extract the current user from the request.

    - auth_mode=none  → anonymous admin
    - auth_mode=local/sso → decode JWT from Authorization header
    """
    if _auth_mode() == "none":
        return ANONYMOUS_USER

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header[7:]
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    from a11yscope.db.models import User

    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return AuthUser(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        must_change_password=user.must_change_password,
        canvas_api_token_encrypted=user.canvas_api_token_encrypted,
    )


def require_role(*allowed_roles: str):
    """Return a dependency that checks the user's role."""

    async def _check(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {', '.join(allowed_roles)}",
            )
        return user

    return _check
