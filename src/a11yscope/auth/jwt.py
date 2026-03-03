"""JWT access token and refresh token creation / validation."""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from a11yscope.config import get_settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7


def create_access_token(
    user_id: str,
    email: str,
    role: str,
    must_change_password: bool = False,
) -> str:
    """Create a signed JWT access token."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "must_change_password": must_change_password,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.effective_secret_key, algorithm=ALGORITHM)


def create_refresh_token() -> tuple[str, str, datetime]:
    """Create a refresh token. Returns (raw_token, sha256_hash, expires_at)."""
    raw = uuid.uuid4().hex + uuid.uuid4().hex  # 64 hex chars
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    return raw, token_hash, expires_at


def decode_access_token(token: str) -> dict | None:
    """Decode and validate a JWT access token. Returns payload or None."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.effective_secret_key, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


def hash_refresh_token(raw: str) -> str:
    """Hash a raw refresh token for storage comparison."""
    return hashlib.sha256(raw.encode()).hexdigest()
