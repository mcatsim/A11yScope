"""Authentication backends — NoAuth, Local, SSO."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AuthUser:
    """Lightweight user object carried through request lifecycle."""
    id: str
    email: str
    display_name: str
    role: str  # admin, auditor, viewer
    must_change_password: bool = False
    canvas_api_token_encrypted: str | None = None


class AuthBackend(ABC):
    """Base class for authentication backends."""

    @abstractmethod
    async def authenticate(self, **kwargs) -> AuthUser | None:
        """Authenticate a user. Returns AuthUser or None."""
        ...


class NoAuthBackend(AuthBackend):
    """auth_mode=none — everyone is anonymous admin."""

    async def authenticate(self, **kwargs) -> AuthUser:
        return AuthUser(
            id="anonymous",
            email="anonymous@localhost",
            display_name="Anonymous",
            role="admin",
        )


ANONYMOUS_USER = AuthUser(
    id="anonymous",
    email="anonymous@localhost",
    display_name="Anonymous",
    role="admin",
)
