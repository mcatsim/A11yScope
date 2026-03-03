# Scan Dashboard UX Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the linear wizard UI with a dashboard-first scan management system supporting multi-scan queuing, item-level progress, DB persistence, encrypted API key storage, and secure-by-design architecture.

**Architecture:** Dashboard SPA (Alpine.js) talks to FastAPI backend via REST + WebSocket. Scans are persisted in SQLite/PostgreSQL via SQLAlchemy. A ScanQueueManager singleton runs one scan per API key concurrently. Canvas API tokens are Fernet-encrypted at rest with HKDF key derivation. All user input is sanitized server-side. Security headers enforced via middleware.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 async, Alembic, cryptography (Fernet/HKDF), Alpine.js, Pico CSS

**Design Doc:** `docs/plans/2026-03-02-scan-dashboard-ux-design.md`

---

## Task 1: Security Headers Middleware

**Rationale:** Security foundation first. Every response gets hardened headers before we build any new features. This prevents CWE-79 (XSS), CWE-693 (clickjacking), and establishes CSP.

**Files:**
- Create: `src/a11yscope/web/middleware/security_headers.py`
- Modify: `src/a11yscope/web/app.py`
- Test: `tests/test_security_headers.py`

**Step 1: Write the failing test**

```python
# tests/test_security_headers.py
import pytest
from httpx import AsyncClient, ASGITransport
from a11yscope.web.app import app

@pytest.mark.asyncio
async def test_security_headers_present():
    """Every response must include hardened security headers."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "default-src 'self'" in resp.headers["Content-Security-Policy"]
    assert "camera=()" in resp.headers["Permissions-Policy"]
    assert resp.headers.get("X-XSS-Protection") == "0"

@pytest.mark.asyncio
async def test_csp_blocks_inline_scripts():
    """CSP must not allow unsafe-inline for scripts."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    csp = resp.headers["Content-Security-Policy"]
    assert "script-src 'self'" in csp
    assert "unsafe-inline" not in csp.split("script-src")[1].split(";")[0]
```

**Step 2: Run test to verify it fails**

Run: `cd ~/Canvas-accessibility-buddy && python -m pytest tests/test_security_headers.py -v`
Expected: FAIL — headers not present

**Step 3: Write the security headers middleware**

```python
# src/a11yscope/web/middleware/__init__.py
# (empty)

# src/a11yscope/web/middleware/security_headers.py
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "0",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "connect-src 'self' wss:; "
        "img-src 'self' data:; "
        "font-src 'self'"
    ),
}

# Paths that carry sensitive data — suppress caching
_SENSITIVE_PREFIXES = ("/api/keys", "/api/scans", "/api/auth", "/api/admin")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach hardened security headers to every HTTP response."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value
        # Prevent caching of sensitive API responses
        if any(request.url.path.startswith(p) for p in _SENSITIVE_PREFIXES):
            response.headers["Cache-Control"] = "no-store"
        return response
```

**Step 4: Register middleware in app.py**

Add to `src/a11yscope/web/app.py` after the existing `RequestIDMiddleware`:

```python
from a11yscope.web.middleware.security_headers import SecurityHeadersMiddleware
app.add_middleware(SecurityHeadersMiddleware)
```

**Step 5: Run test to verify it passes**

Run: `cd ~/Canvas-accessibility-buddy && python -m pytest tests/test_security_headers.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/a11yscope/web/middleware/ tests/test_security_headers.py src/a11yscope/web/app.py
git commit -m "feat: add security headers middleware (CSP, X-Frame-Options, etc.)"
```

---

## Task 2: Key Encryption Service

**Rationale:** Before we can store API keys, we need the encryption layer. Uses Fernet with HKDF key derivation from SECRET_KEY (key separation — CWE-312 mitigation). This is the foundation for all key storage.

**Files:**
- Create: `src/a11yscope/crypto.py`
- Test: `tests/test_crypto.py`

**Step 1: Write the failing test**

```python
# tests/test_crypto.py
import pytest
from a11yscope.crypto import encrypt_token, decrypt_token, mask_token

def test_encrypt_decrypt_roundtrip():
    """Encrypted token must decrypt to original value."""
    secret = "test-secret-key-at-least-32-chars-long"
    token = "canvas_api_token_abc123xyz"
    encrypted = encrypt_token(token, secret)
    assert isinstance(encrypted, bytes)
    assert token.encode() not in encrypted  # must not contain plaintext
    decrypted = decrypt_token(encrypted, secret)
    assert decrypted == token

def test_different_secrets_fail():
    """Decrypting with wrong secret must raise."""
    encrypted = encrypt_token("my-token", "secret-one-at-least-32-characters")
    with pytest.raises(Exception):
        decrypt_token(encrypted, "secret-two-at-least-32-characters")

def test_mask_token():
    """mask_token shows only last 4 characters."""
    assert mask_token("abcdefghijklmnop") == "************mnop"
    assert mask_token("ab") == "ab"  # short tokens returned as-is

def test_tampered_ciphertext_rejected():
    """Modified ciphertext must be rejected (Fernet HMAC)."""
    secret = "test-secret-key-at-least-32-chars-long"
    encrypted = encrypt_token("my-token", secret)
    tampered = encrypted[:-4] + b"XXXX"
    with pytest.raises(Exception):
        decrypt_token(tampered, secret)
```

**Step 2: Run test to verify it fails**

Run: `cd ~/Canvas-accessibility-buddy && python -m pytest tests/test_crypto.py -v`
Expected: FAIL — module not found

**Step 3: Write the crypto module**

```python
# src/a11yscope/crypto.py
"""
Symmetric encryption for sensitive fields (Canvas API tokens).

Uses Fernet (AES-128-CBC + HMAC-SHA256) with HKDF key derivation
so the encryption key is separated from the application SECRET_KEY.
"""

import base64

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes


_INFO = b"a11yscope-token-encryption"


def _derive_key(secret: str) -> bytes:
    """Derive a Fernet-compatible key from the application secret."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,  # deterministic derivation
        info=_INFO,
    )
    raw = hkdf.derive(secret.encode())
    return base64.urlsafe_b64encode(raw)


def encrypt_token(plaintext: str, secret: str) -> bytes:
    """Encrypt a plaintext token. Returns Fernet ciphertext bytes."""
    f = Fernet(_derive_key(secret))
    return f.encrypt(plaintext.encode())


def decrypt_token(ciphertext: bytes, secret: str) -> str:
    """Decrypt a Fernet ciphertext. Raises on tamper or wrong key."""
    f = Fernet(_derive_key(secret))
    try:
        return f.decrypt(ciphertext).decode()
    except InvalidToken:
        raise ValueError("Cannot decrypt token — wrong key or tampered ciphertext")


def mask_token(token: str) -> str:
    """Return a masked version showing only the last 4 characters."""
    if len(token) <= 4:
        return token
    return "*" * (len(token) - 4) + token[-4:]
```

**Step 4: Run test to verify it passes**

Run: `cd ~/Canvas-accessibility-buddy && python -m pytest tests/test_crypto.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/a11yscope/crypto.py tests/test_crypto.py
git commit -m "feat: add Fernet encryption service with HKDF key derivation"
```

---

## Task 3: Database Models & Migration

**Rationale:** Add the three new tables (api_keys, audit_jobs, audit_job_items) to the ORM and create the Alembic migration. These tables are the persistence backbone for the entire feature.

**Files:**
- Modify: `src/a11yscope/db/models.py`
- Create: `src/a11yscope/db/migrations/versions/002_scan_dashboard.py`
- Modify: `src/a11yscope/audit_log/schemas.py` (new audit actions)
- Test: `tests/test_db_models.py`

**Step 1: Write the failing test**

```python
# tests/test_db_models.py
import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from a11yscope.db.models import Base, ApiKey, AuditJob, AuditJobItem

@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()

@pytest.mark.asyncio
async def test_api_key_model(db_session):
    """ApiKey model stores encrypted token as bytes."""
    key = ApiKey(
        user_id="user-1",
        name="My Token",
        canvas_url="https://canvas.example.edu",
        encrypted_token=b"encrypted-bytes-here",
        token_hint="x123",
    )
    db_session.add(key)
    await db_session.commit()
    await db_session.refresh(key)
    assert key.id is not None
    assert key.encrypted_token == b"encrypted-bytes-here"
    assert key.token_hint == "x123"

@pytest.mark.asyncio
async def test_audit_job_model(db_session):
    """AuditJob persists scan state."""
    # Need an api_key first
    key = ApiKey(
        user_id="user-1", name="T", canvas_url="https://c.edu",
        encrypted_token=b"enc", token_hint="hint",
    )
    db_session.add(key)
    await db_session.commit()
    await db_session.refresh(key)

    job = AuditJob(
        user_id="user-1",
        api_key_id=key.id,
        canvas_url="https://c.edu",
        course_id=101,
        course_name="CS101",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    assert job.status == "queued"
    assert job.progress_pct == 0

@pytest.mark.asyncio
async def test_audit_job_items_cascade_delete(db_session):
    """Deleting a job cascades to its items."""
    key = ApiKey(
        user_id="u1", name="T", canvas_url="https://c.edu",
        encrypted_token=b"e", token_hint="h",
    )
    db_session.add(key)
    await db_session.commit()
    await db_session.refresh(key)

    job = AuditJob(
        user_id="u1", api_key_id=key.id, canvas_url="https://c.edu",
        course_id=1, course_name="C",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    item = AuditJobItem(
        job_id=job.id, item_type="page", item_title="Syllabus", sort_order=0,
    )
    db_session.add(item)
    await db_session.commit()

    await db_session.delete(job)
    await db_session.commit()

    from sqlalchemy import select
    result = await db_session.execute(select(AuditJobItem))
    assert result.scalars().all() == []
```

**Step 2: Run test to verify it fails**

Run: `cd ~/Canvas-accessibility-buddy && python -m pytest tests/test_db_models.py -v`
Expected: FAIL — models not found

**Step 3: Add models to `src/a11yscope/db/models.py`**

Append after existing models:

```python
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

    items = relationship("AuditJobItem", back_populates="job", cascade="all, delete-orphan")

class AuditJobItem(Base):
    __tablename__ = "audit_job_items"

    id = Column(String, primary_key=True, default=_new_uuid)
    job_id = Column(String, ForeignKey("audit_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    item_type = Column(String, nullable=False)
    item_title = Column(String(200), nullable=False)
    status = Column(String, nullable=False, default="pending")
    issues = Column(Integer, nullable=False, default=0)
    checked_at = Column(DateTime, nullable=True)
    sort_order = Column(Integer, nullable=False)

    job = relationship("AuditJob", back_populates="items")
```

Add `LargeBinary` to the Column imports at top of file if not present.

**Step 4: Create migration file**

```python
# src/a11yscope/db/migrations/versions/002_scan_dashboard.py
"""Add api_keys, audit_jobs, audit_job_items tables for scan dashboard.

Revision ID: 002
Revises: 001
"""

import sqlalchemy as sa
from alembic import op

revision = "002"
down_revision = "001"


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("canvas_url", sa.String(), nullable=False),
        sa.Column("encrypted_token", sa.LargeBinary(), nullable=False),
        sa.Column("token_hint", sa.String(4), nullable=False),
        sa.Column("course_count", sa.Integer(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_api_keys_user_id", "api_keys", ["user_id"])

    op.create_table(
        "audit_jobs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("api_key_id", sa.String(), sa.ForeignKey("api_keys.id"), nullable=False),
        sa.Column("canvas_url", sa.String(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("course_name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="queued"),
        sa.Column("progress_pct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_phase", sa.String(), nullable=True),
        sa.Column("current_item", sa.String(), nullable=True),
        sa.Column("items_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_checked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("issues_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("queued_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("checkpoint_json", sa.Text(), nullable=True),
        sa.Column("queue_position", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("idx_audit_jobs_user_id", "audit_jobs", ["user_id"])
    op.create_index("idx_audit_jobs_status", "audit_jobs", ["status"])

    op.create_table(
        "audit_job_items",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("job_id", sa.String(), sa.ForeignKey("audit_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_type", sa.String(), nullable=False),
        sa.Column("item_title", sa.String(200), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("issues", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("checked_at", sa.DateTime(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
    )
    op.create_index("idx_audit_job_items_job_id", "audit_job_items", ["job_id"])


def downgrade() -> None:
    op.drop_table("audit_job_items")
    op.drop_table("audit_jobs")
    op.drop_table("api_keys")
```

**Step 5: Add new audit actions to `src/a11yscope/audit_log/schemas.py`**

Append to the `AuditAction` enum:

```python
    # API Keys
    KEY_CREATED = "key.created"
    KEY_UPDATED = "key.updated"
    KEY_DELETED = "key.deleted"

    # Scans (new)
    SCAN_QUEUED = "scan.queued"
    SCAN_STARTED = "scan.started"
    SCAN_COMPLETED = "scan.completed"
    SCAN_FAILED = "scan.failed"
    SCAN_CANCELLED = "scan.cancelled"
    SCAN_RESUMED = "scan.resumed"
```

**Step 6: Run test to verify it passes**

Run: `cd ~/Canvas-accessibility-buddy && python -m pytest tests/test_db_models.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add src/a11yscope/db/models.py src/a11yscope/db/migrations/versions/002_scan_dashboard.py \
        src/a11yscope/audit_log/schemas.py tests/test_db_models.py
git commit -m "feat: add api_keys, audit_jobs, audit_job_items models and migration"
```

---

## Task 4: Input Sanitization Utility

**Rationale:** Canvas content titles are user-generated and could contain HTML/scripts. Server-side sanitization prevents stored XSS (CWE-79). This utility is used everywhere we persist Canvas-sourced strings.

**Files:**
- Create: `src/a11yscope/sanitize.py`
- Test: `tests/test_sanitize.py`

**Step 1: Write the failing test**

```python
# tests/test_sanitize.py
from a11yscope.sanitize import sanitize_title

def test_strips_html_tags():
    assert sanitize_title("<b>Bold</b> text") == "Bold text"

def test_strips_script_tags():
    assert "script" not in sanitize_title('<script>alert("xss")</script>Hello')
    assert "Hello" in sanitize_title('<script>alert("xss")</script>Hello')

def test_truncates_to_max_length():
    long_title = "A" * 300
    result = sanitize_title(long_title)
    assert len(result) == 200

def test_strips_null_bytes():
    assert sanitize_title("Hello\x00World") == "HelloWorld"

def test_normalizes_whitespace():
    assert sanitize_title("  too   many   spaces  ") == "too many spaces"

def test_empty_string():
    assert sanitize_title("") == ""
    assert sanitize_title(None) == ""
```

**Step 2: Run test to verify it fails**

Run: `cd ~/Canvas-accessibility-buddy && python -m pytest tests/test_sanitize.py -v`
Expected: FAIL

**Step 3: Write the sanitization module**

```python
# src/a11yscope/sanitize.py
"""Input sanitization for Canvas-sourced strings.

All content titles from Canvas are user-generated and must be
sanitized before storage to prevent stored XSS (CWE-79).
"""

import re

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_MAX_TITLE_LENGTH = 200


def sanitize_title(value: str | None, max_length: int = _MAX_TITLE_LENGTH) -> str:
    """Strip HTML tags, null bytes, normalize whitespace, truncate."""
    if not value:
        return ""
    # Remove null bytes
    text = value.replace("\x00", "")
    # Strip all HTML tags
    text = _TAG_RE.sub("", text)
    # Normalize whitespace
    text = _WHITESPACE_RE.sub(" ", text).strip()
    # Truncate
    return text[:max_length]
```

**Step 4: Run test to verify it passes**

Run: `cd ~/Canvas-accessibility-buddy && python -m pytest tests/test_sanitize.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/a11yscope/sanitize.py tests/test_sanitize.py
git commit -m "feat: add input sanitization for Canvas-sourced strings (CWE-79)"
```

---

## Task 5: API Keys Routes

**Rationale:** Users need to save, list, and delete Canvas API keys before they can start scans. Keys are encrypted at rest, never returned in plaintext, and scoped to the authenticated user.

**Files:**
- Create: `src/a11yscope/web/api/key_routes.py`
- Modify: `src/a11yscope/web/app.py` (register router)
- Test: `tests/test_key_routes.py`

**Step 1: Write the failing test**

```python
# tests/test_key_routes.py
import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from a11yscope.web.app import app
from a11yscope.auth.backend import AuthUser

MOCK_USER = AuthUser(
    id="user-1", email="test@test.com",
    display_name="Test", role="auditor",
)

@pytest.fixture
def auth_override():
    """Override auth to return a mock user."""
    from a11yscope.auth.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    yield
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_create_key(auth_override):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/keys", json={
            "name": "My Canvas",
            "canvas_url": "https://canvas.example.edu",
            "token": "test-canvas-api-token-1234567890",
        })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Canvas"
    assert data["canvas_url"] == "https://canvas.example.edu"
    assert data["token_hint"] == "7890"
    assert "encrypted_token" not in data  # never exposed
    assert "token" not in data  # never echoed back

@pytest.mark.asyncio
async def test_list_keys_user_scoped(auth_override):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a key
        await client.post("/api/keys", json={
            "name": "K1", "canvas_url": "https://c.edu",
            "token": "token-abcdefghijklmnop",
        })
        resp = await client.get("/api/keys")
    assert resp.status_code == 200
    keys = resp.json()
    assert len(keys) >= 1
    assert all("token" not in k for k in keys)

@pytest.mark.asyncio
async def test_create_key_rejects_http_url(auth_override):
    """Canvas URL must be HTTPS (CWE-918 / SSRF prevention)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/keys", json={
            "name": "Bad",
            "canvas_url": "http://canvas.example.edu",
            "token": "token-abcdefghijklmnop",
        })
    assert resp.status_code == 422

@pytest.mark.asyncio
async def test_create_key_rejects_xss_name(auth_override):
    """Key name must be safe characters only."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/keys", json={
            "name": '<script>alert("xss")</script>',
            "canvas_url": "https://canvas.example.edu",
            "token": "token-abcdefghijklmnop",
        })
    assert resp.status_code == 422
```

**Step 2: Run test to verify it fails**

Run: `cd ~/Canvas-accessibility-buddy && python -m pytest tests/test_key_routes.py -v`
Expected: FAIL

**Step 3: Write the key routes**

```python
# src/a11yscope/web/api/key_routes.py
"""API key management routes.

Canvas API tokens are Fernet-encrypted at rest and never
returned to the client in plaintext (CWE-312).
"""

import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from a11yscope.auth.backend import AuthUser
from a11yscope.auth.dependencies import get_current_user
from a11yscope.audit_log.logger import AuditLogger, get_audit_logger
from a11yscope.audit_log.schemas import AuditAction
from a11yscope.config import get_settings
from a11yscope.crypto import encrypt_token, mask_token
from a11yscope.db.models import ApiKey
from a11yscope.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

_SAFE_NAME_RE = re.compile(r"^[\w\s\-\.]+$")


class SaveKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    canvas_url: str = Field(..., min_length=10)
    token: str = Field(..., min_length=20, max_length=200)

    @field_validator("name")
    @classmethod
    def name_safe_chars(cls, v: str) -> str:
        if not _SAFE_NAME_RE.match(v):
            raise ValueError("Name must contain only letters, numbers, spaces, hyphens, dots")
        return v.strip()

    @field_validator("canvas_url")
    @classmethod
    def url_must_be_https(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError("Canvas URL must use HTTPS")
        return v.rstrip("/")


class KeyResponse(BaseModel):
    id: str
    name: str
    canvas_url: str
    token_hint: str
    course_count: int | None
    last_used_at: str | None
    created_at: str


@router.post("/keys", status_code=201)
async def create_key(
    req: SaveKeyRequest,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> KeyResponse:
    """Save an encrypted Canvas API key."""
    settings = get_settings()
    encrypted = encrypt_token(req.token, settings.effective_secret_key)
    hint = req.token[-4:]

    key = ApiKey(
        user_id=user.id,
        name=req.name,
        canvas_url=req.canvas_url,
        encrypted_token=encrypted,
        token_hint=hint,
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)

    await audit.log(
        AuditAction.KEY_CREATED, user=user,
        resource_type="api_key", resource_id=key.id,
        detail={"name": req.name, "canvas_url": req.canvas_url},
    )

    return KeyResponse(
        id=key.id, name=key.name, canvas_url=key.canvas_url,
        token_hint=hint, course_count=key.course_count,
        last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
        created_at=key.created_at.isoformat(),
    )


@router.get("/keys")
async def list_keys(
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[KeyResponse]:
    """List the current user's saved API keys (tokens masked)."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == user.id).order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()
    return [
        KeyResponse(
            id=k.id, name=k.name, canvas_url=k.canvas_url,
            token_hint=k.token_hint, course_count=k.course_count,
            last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
            created_at=k.created_at.isoformat(),
        )
        for k in keys
    ]


@router.delete("/keys/{key_id}", status_code=204)
async def delete_key(
    key_id: str,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> None:
    """Delete a saved API key. User-scoped."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id)
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    await db.delete(key)
    await db.commit()
    await audit.log(
        AuditAction.KEY_DELETED, user=user,
        resource_type="api_key", resource_id=key_id,
    )
```

**Step 4: Register in app.py**

Add to `src/a11yscope/web/app.py`:

```python
from a11yscope.web.api.key_routes import router as key_router
app.include_router(key_router, prefix="/api")
```

**Step 5: Run test to verify it passes**

Run: `cd ~/Canvas-accessibility-buddy && python -m pytest tests/test_key_routes.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/a11yscope/web/api/key_routes.py src/a11yscope/web/app.py tests/test_key_routes.py
git commit -m "feat: add API key management routes with Fernet encryption"
```

---

## Task 6: ScanQueueManager

**Rationale:** Core engine that manages scan execution — sequential per API key, parallel across keys, with DB persistence. This replaces the ad-hoc `asyncio.create_task()` approach.

**Files:**
- Create: `src/a11yscope/web/queue_manager.py`
- Test: `tests/test_queue_manager.py`

**Step 1: Write the failing test**

```python
# tests/test_queue_manager.py
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from a11yscope.web.queue_manager import ScanQueueManager

@pytest.fixture
def manager():
    return ScanQueueManager()

@pytest.mark.asyncio
async def test_enqueue_creates_job(manager):
    """Enqueuing returns a job ID and the job is tracked."""
    job_id = await manager.enqueue(
        user_id="u1", api_key_id="k1", canvas_url="https://c.edu",
        course_id=101, course_name="CS101",
        db_session_factory=AsyncMock(),
        decrypt_fn=lambda kid: "plaintext-token",
    )
    assert isinstance(job_id, str)
    status = manager.get_job_status(job_id)
    assert status is not None
    assert status["status"] in ("queued", "running")

@pytest.mark.asyncio
async def test_sequential_per_key(manager):
    """Jobs with the same key run sequentially."""
    started = []
    original_run = manager._execute_job

    async def slow_run(job_id, **kwargs):
        started.append(job_id)
        await asyncio.sleep(0.1)

    manager._execute_job = slow_run

    id1 = await manager.enqueue(
        user_id="u1", api_key_id="k1", canvas_url="https://c.edu",
        course_id=1, course_name="C1",
        db_session_factory=AsyncMock(), decrypt_fn=lambda kid: "tok",
    )
    id2 = await manager.enqueue(
        user_id="u1", api_key_id="k1", canvas_url="https://c.edu",
        course_id=2, course_name="C2",
        db_session_factory=AsyncMock(), decrypt_fn=lambda kid: "tok",
    )
    # Give workers time to process
    await asyncio.sleep(0.05)
    # First job should start before second
    assert started[0] == id1

@pytest.mark.asyncio
async def test_cancel_queued_job(manager):
    """Cancelling a queued job removes it."""
    manager._execute_job = AsyncMock(side_effect=asyncio.sleep(10))
    id1 = await manager.enqueue(
        user_id="u1", api_key_id="k1", canvas_url="https://c.edu",
        course_id=1, course_name="C1",
        db_session_factory=AsyncMock(), decrypt_fn=lambda kid: "tok",
    )
    cancelled = manager.cancel(id1)
    assert cancelled is True
```

**Step 2: Run test to verify it fails**

Run: `cd ~/Canvas-accessibility-buddy && python -m pytest tests/test_queue_manager.py -v`
Expected: FAIL

**Step 3: Write the queue manager**

```python
# src/a11yscope/web/queue_manager.py
"""Scan queue manager — sequential per API key, parallel across keys.

Each API key gets its own asyncio worker coroutine. Jobs for the same
key are processed in FIFO order. Different keys run concurrently.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class QueuedJob:
    job_id: str
    user_id: str
    api_key_id: str
    canvas_url: str
    course_id: int
    course_name: str
    status: str = "queued"  # queued, running, complete, failed, cancelled
    progress_pct: int = 0
    current_phase: str | None = None
    current_item: str | None = None
    items_total: int = 0
    items_checked: int = 0
    issues_found: int = 0
    error: str | None = None
    progress_log: list[dict[str, Any]] = field(default_factory=list)
    db_session_factory: Any = None
    decrypt_fn: Callable | None = None
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ScanQueueManager:
    """Manages scan execution with per-key sequential processing."""

    def __init__(self) -> None:
        self._jobs: dict[str, QueuedJob] = {}
        self._key_queues: dict[str, asyncio.Queue[str]] = {}
        self._workers: dict[str, asyncio.Task] = {}

    async def enqueue(
        self,
        user_id: str,
        api_key_id: str,
        canvas_url: str,
        course_id: int,
        course_name: str,
        db_session_factory: Any,
        decrypt_fn: Callable,
    ) -> str:
        """Add a scan job to the queue. Returns job_id."""
        job_id = uuid.uuid4().hex[:12]
        job = QueuedJob(
            job_id=job_id,
            user_id=user_id,
            api_key_id=api_key_id,
            canvas_url=canvas_url,
            course_id=course_id,
            course_name=course_name,
            db_session_factory=db_session_factory,
            decrypt_fn=decrypt_fn,
        )
        self._jobs[job_id] = job

        # Ensure a queue + worker exists for this key
        if api_key_id not in self._key_queues:
            self._key_queues[api_key_id] = asyncio.Queue()
            self._workers[api_key_id] = asyncio.create_task(
                self._worker_loop(api_key_id)
            )

        await self._key_queues[api_key_id].put(job_id)
        logger.info("Enqueued job %s for key %s (course %d)", job_id, api_key_id[:8], course_id)
        return job_id

    async def _worker_loop(self, api_key_id: str) -> None:
        """Process jobs for a single API key sequentially."""
        queue = self._key_queues[api_key_id]
        while True:
            job_id = await queue.get()
            job = self._jobs.get(job_id)
            if not job or job.status == "cancelled":
                queue.task_done()
                continue
            try:
                job.status = "running"
                await self._execute_job(job_id)
            except Exception as exc:
                logger.exception("Job %s failed", job_id)
                if job_id in self._jobs:
                    self._jobs[job_id].status = "failed"
                    self._jobs[job_id].error = str(exc)
            finally:
                queue.task_done()

    async def _execute_job(self, job_id: str, **kwargs: Any) -> None:
        """Run the actual audit. Override in tests."""
        # Real implementation will call audit_runner.run_audit()
        # This is a placeholder — Task 8 will wire it up
        job = self._jobs[job_id]
        job.status = "complete"

    def get_job_status(self, job_id: str) -> dict[str, Any] | None:
        """Get current status of a job."""
        job = self._jobs.get(job_id)
        if not job:
            return None
        return {
            "job_id": job.job_id,
            "status": job.status,
            "course_id": job.course_id,
            "course_name": job.course_name,
            "progress_pct": job.progress_pct,
            "current_phase": job.current_phase,
            "current_item": job.current_item,
            "items_total": job.items_total,
            "items_checked": job.items_checked,
            "issues_found": job.issues_found,
            "error": job.error,
        }

    def cancel(self, job_id: str) -> bool:
        """Cancel a job. Returns True if cancelled."""
        job = self._jobs.get(job_id)
        if not job:
            return False
        if job.status in ("complete", "failed"):
            return False
        job.status = "cancelled"
        job.cancel_event.set()
        return True

    def get_user_jobs(self, user_id: str) -> list[dict[str, Any]]:
        """Get all jobs for a user."""
        return [
            self.get_job_status(jid)
            for jid, j in self._jobs.items()
            if j.user_id == user_id
        ]

    def get_queue_for_key(self, api_key_id: str) -> list[str]:
        """Get ordered list of queued job IDs for a key."""
        return [
            jid for jid, j in self._jobs.items()
            if j.api_key_id == api_key_id and j.status == "queued"
        ]
```

**Step 4: Run test to verify it passes**

Run: `cd ~/Canvas-accessibility-buddy && python -m pytest tests/test_queue_manager.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/a11yscope/web/queue_manager.py tests/test_queue_manager.py
git commit -m "feat: add ScanQueueManager with per-key sequential processing"
```

---

## Task 7: Scan Routes (CRUD + Queue)

**Rationale:** REST endpoints for creating, listing, cancelling, and resuming scans. These are the API surface the frontend will call.

**Files:**
- Create: `src/a11yscope/web/api/scan_routes.py`
- Modify: `src/a11yscope/web/app.py` (register router + queue manager lifecycle)
- Test: `tests/test_scan_routes.py`

**Step 1: Write the failing test**

```python
# tests/test_scan_routes.py
import pytest
from httpx import AsyncClient, ASGITransport
from a11yscope.web.app import app
from a11yscope.auth.backend import AuthUser

MOCK_USER = AuthUser(id="u1", email="t@t.com", display_name="T", role="auditor")

@pytest.fixture
def auth_override():
    from a11yscope.auth.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    yield
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_create_scan_requires_key_id(auth_override):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/scans", json={
            "course_ids": [101],
        })
    assert resp.status_code == 422  # missing key_id

@pytest.mark.asyncio
async def test_create_scan_rejects_empty_courses(auth_override):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/scans", json={
            "key_id": "some-key-id",
            "course_ids": [],
        })
    assert resp.status_code == 422  # min_length=1

@pytest.mark.asyncio
async def test_create_scan_rejects_duplicate_courses(auth_override):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/scans", json={
            "key_id": "some-key-id",
            "course_ids": [101, 101],
        })
    assert resp.status_code == 422  # duplicate IDs

@pytest.mark.asyncio
async def test_list_scans_empty(auth_override):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/scans")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
```

**Step 2: Run test to verify it fails**

Run: `cd ~/Canvas-accessibility-buddy && python -m pytest tests/test_scan_routes.py -v`
Expected: FAIL

**Step 3: Write the scan routes**

```python
# src/a11yscope/web/api/scan_routes.py
"""Scan management routes — create, list, cancel, resume scans."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from a11yscope.auth.backend import AuthUser
from a11yscope.auth.dependencies import get_current_user
from a11yscope.audit_log.logger import AuditLogger, get_audit_logger
from a11yscope.audit_log.schemas import AuditAction
from a11yscope.config import get_settings
from a11yscope.crypto import decrypt_token
from a11yscope.db.models import ApiKey, AuditJob
from a11yscope.db.session import get_db, get_session_factory

logger = logging.getLogger(__name__)

router = APIRouter()

# The queue manager instance is set during app startup (see app.py lifespan)
_queue_manager = None

def set_queue_manager(qm):
    global _queue_manager
    _queue_manager = qm

def get_queue_manager():
    if _queue_manager is None:
        raise RuntimeError("Queue manager not initialized")
    return _queue_manager


class CreateScanRequest(BaseModel):
    key_id: str
    course_ids: list[int] = Field(..., min_length=1, max_length=50)

    @field_validator("course_ids")
    @classmethod
    def no_duplicates(cls, v: list[int]) -> list[int]:
        if len(v) != len(set(v)):
            raise ValueError("Duplicate course IDs not allowed")
        return v


class ScanResponse(BaseModel):
    job_id: str
    status: str
    course_id: int
    course_name: str
    progress_pct: int = 0


@router.post("/scans", status_code=201)
async def create_scans(
    req: CreateScanRequest,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> list[ScanResponse]:
    """Queue one or more scans. Returns list of created jobs."""
    # Verify user owns the key
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == req.key_id, ApiKey.user_id == user.id)
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    settings = get_settings()
    qm = get_queue_manager()
    factory = get_session_factory()

    def _decrypt(key_id: str) -> str:
        return decrypt_token(key.encrypted_token, settings.effective_secret_key)

    jobs = []
    for course_id in req.course_ids:
        job_id = await qm.enqueue(
            user_id=user.id,
            api_key_id=req.key_id,
            canvas_url=key.canvas_url,
            course_id=course_id,
            course_name=f"Course {course_id}",  # Will be resolved during scan
            db_session_factory=factory,
            decrypt_fn=_decrypt,
        )
        jobs.append(ScanResponse(
            job_id=job_id, status="queued",
            course_id=course_id, course_name=f"Course {course_id}",
        ))

    await audit.log(
        AuditAction.SCAN_QUEUED, user=user,
        resource_type="scan", resource_id=req.key_id,
        detail={"course_ids": req.course_ids, "count": len(req.course_ids)},
    )

    return jobs


@router.get("/scans")
async def list_scans(
    user: AuthUser = Depends(get_current_user),
) -> list[ScanResponse]:
    """List all scans for the current user."""
    qm = get_queue_manager()
    user_jobs = qm.get_user_jobs(user.id)
    return [
        ScanResponse(
            job_id=j["job_id"], status=j["status"],
            course_id=j["course_id"], course_name=j["course_name"],
            progress_pct=j["progress_pct"],
        )
        for j in user_jobs
        if j is not None
    ]


@router.get("/scans/{job_id}")
async def get_scan(
    job_id: str,
    user: AuthUser = Depends(get_current_user),
) -> dict:
    """Get detailed scan status."""
    qm = get_queue_manager()
    status = qm.get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Scan not found")
    # Verify ownership
    job = qm._jobs.get(job_id)
    if job and job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Scan not found")
    return status


@router.delete("/scans/{job_id}", status_code=204)
async def cancel_scan(
    job_id: str,
    user: AuthUser = Depends(get_current_user),
    audit: AuditLogger = Depends(get_audit_logger),
) -> None:
    """Cancel a queued or running scan."""
    qm = get_queue_manager()
    job = qm._jobs.get(job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Scan not found")
    if not qm.cancel(job_id):
        raise HTTPException(status_code=409, detail="Cannot cancel completed scan")
    await audit.log(
        AuditAction.SCAN_CANCELLED, user=user,
        resource_type="scan", resource_id=job_id,
    )
```

**Step 4: Register router and queue manager in app.py**

Add to `src/a11yscope/web/app.py`:

In the lifespan function, after `seed_admin`:
```python
    from a11yscope.web.queue_manager import ScanQueueManager
    from a11yscope.web.api.scan_routes import set_queue_manager
    queue_manager = ScanQueueManager()
    set_queue_manager(queue_manager)
```

And register the router:
```python
from a11yscope.web.api.scan_routes import router as scan_router
app.include_router(scan_router, prefix="/api")
```

**Step 5: Run test to verify it passes**

Run: `cd ~/Canvas-accessibility-buddy && python -m pytest tests/test_scan_routes.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/a11yscope/web/api/scan_routes.py src/a11yscope/web/app.py tests/test_scan_routes.py
git commit -m "feat: add scan CRUD routes with queue integration"
```

---

## Task 8: WebSocket Protocol Update

**Rationale:** Move from query-param auth to first-message auth (CWE-598 fix). Add item-level message types for the live feed. Support reconnection replay.

**Files:**
- Create: `src/a11yscope/web/api/scan_ws.py` (new WS endpoint)
- Modify: `src/a11yscope/web/app.py` (register)
- Test: `tests/test_scan_ws.py`

**Step 1: Write the failing test**

```python
# tests/test_scan_ws.py
import pytest
import asyncio
from unittest.mock import patch
from httpx import ASGITransport
from starlette.testclient import TestClient
from a11yscope.web.app import app
from a11yscope.web.queue_manager import QueuedJob

def test_ws_rejects_without_auth():
    """WebSocket must reject connections with no auth message."""
    client = TestClient(app)
    with client.websocket_connect("/ws/scan/fake-job-id") as ws:
        # Server should close within 5 seconds if no auth sent
        import time
        time.sleep(0.5)
        # Send a non-auth message
        ws.send_json({"type": "ping"})
        msg = ws.receive_json()
        assert msg["type"] == "error"

def test_ws_accepts_valid_auth():
    """WebSocket accepts connection with valid auth message."""
    # This test requires a valid JWT — will be integration-tested
    pass  # Placeholder for integration test in Task 11
```

**Step 2: Write the new WebSocket endpoint**

```python
# src/a11yscope/web/api/scan_ws.py
"""WebSocket endpoint for scan progress streaming.

Auth is via first message (not URL query param) to prevent
token leakage in server logs (CWE-598).
"""

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from a11yscope.auth.jwt import decode_access_token
from a11yscope.config import get_settings
from a11yscope.web.api.scan_routes import get_queue_manager

logger = logging.getLogger(__name__)

router = APIRouter()

_AUTH_TIMEOUT_SECONDS = 5


@router.websocket("/ws/scan/{job_id}")
async def scan_ws(websocket: WebSocket, job_id: str):
    """Stream scan progress over WebSocket with first-message auth."""
    await websocket.accept()

    settings = get_settings()
    user_id = "anonymous"

    # --- Auth phase ---
    if settings.auth_mode != "none":
        try:
            msg = await asyncio.wait_for(
                websocket.receive_json(),
                timeout=_AUTH_TIMEOUT_SECONDS,
            )
        except (asyncio.TimeoutError, Exception):
            await websocket.send_json({"type": "error", "message": "Auth timeout"})
            await websocket.close(code=4001)
            return

        if msg.get("type") != "auth" or not msg.get("token"):
            await websocket.send_json({"type": "error", "message": "Expected auth message"})
            await websocket.close(code=4001)
            return

        payload = decode_access_token(msg["token"])
        if payload is None:
            await websocket.send_json({"type": "error", "message": "Invalid token"})
            await websocket.close(code=4001)
            return

        user_id = payload["sub"]

    # --- Resolve job ---
    qm = get_queue_manager()
    job = qm._jobs.get(job_id)
    if not job:
        await websocket.send_json({"type": "error", "message": "Job not found"})
        await websocket.close()
        return

    # Verify ownership
    if settings.auth_mode != "none" and job.user_id != user_id:
        await websocket.send_json({"type": "error", "message": "Access denied"})
        await websocket.close(code=4003)
        return

    # --- Replay existing progress (for reconnection) ---
    for msg in job.progress_log:
        await websocket.send_json(msg)

    # --- Stream new progress ---
    last_idx = len(job.progress_log)
    try:
        while True:
            if last_idx < len(job.progress_log):
                for msg in job.progress_log[last_idx:]:
                    await websocket.send_json(msg)
                last_idx = len(job.progress_log)

            if job.status in ("complete", "failed", "cancelled"):
                break

            await asyncio.sleep(0.3)
    except WebSocketDisconnect:
        logger.debug("WebSocket disconnected for job %s", job_id)
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
```

**Step 3: Register in app.py**

```python
from a11yscope.web.api.scan_ws import router as scan_ws_router
app.include_router(scan_ws_router)
```

**Step 4: Run tests**

Run: `cd ~/Canvas-accessibility-buddy && python -m pytest tests/test_scan_ws.py -v`

**Step 5: Commit**

```bash
git add src/a11yscope/web/api/scan_ws.py src/a11yscope/web/app.py tests/test_scan_ws.py
git commit -m "feat: add WebSocket endpoint with first-message auth (CWE-598)"
```

---

## Task 9: Frontend — Dashboard Shell & Navigation

**Rationale:** Replace the wizard-based SPA with the dashboard layout. This task builds the shell (sidebar nav, view routing, header) without scan functionality — just the skeleton.

**Files:**
- Modify: `src/a11yscope/web/static/index.html` (new layout)
- Modify: `src/a11yscope/web/static/app.js` (dashboard Alpine.js app)

**Step 1: Implement the dashboard HTML shell**

Replace the wizard-based `index.html` with the dashboard layout. Keep the existing `<head>` (Pico CSS), but replace `<body>` with:

- Sidebar nav (Dashboard, API Keys, History, Admin)
- Main content area with view switching via Alpine.js `x-show`
- `[+ New Scan]` button in header
- Mobile-responsive sidebar toggle

**Step 2: Implement the Alpine.js dashboard app**

Rewrite `app.js` with a new `dashboardApp()` function:

- `currentView`: tracks active view (dashboard, keys, history, admin)
- `activeScans`, `queuedScans`, `recentScans`: arrays populated from `/api/scans`
- `savedKeys`: array from `/api/keys`
- `showNewScanModal`: boolean for modal visibility
- `selectedScanId`: for drill-down into scan detail
- Polling: `setInterval` to refresh scan status every 2 seconds
- WebSocket connections: one per active scan for live updates
- `fetchWithAuth()`: existing helper, updated to use HttpOnly cookies (remove localStorage token)

**Step 3: Build incrementally**

Start with just the sidebar + dashboard view showing placeholder text. Wire up the view switching. Verify navigation works by running the app locally:

```bash
cd ~/Canvas-accessibility-buddy && python -m a11yscope
```

Open `http://localhost:8080` and verify sidebar nav switches views.

**Step 4: Commit**

```bash
git add src/a11yscope/web/static/index.html src/a11yscope/web/static/app.js
git commit -m "feat: replace wizard UI with dashboard shell and sidebar navigation"
```

---

## Task 10: Frontend — Dashboard Content (Active, Queue, Recent)

**Rationale:** Populate the dashboard with live data from the `/api/scans` and `/api/keys` endpoints.

**Files:**
- Modify: `src/a11yscope/web/static/app.js`
- Modify: `src/a11yscope/web/static/index.html`

**Step 1: Active Scans section**

- Cards for each running scan showing: course name, progress bar, phase, current item, issue count
- Cards are clickable (sets `selectedScanId` to show detail view)
- WebSocket connection per active scan for real-time updates

**Step 2: Queue section**

- Ordered list of queued scans with position numbers
- Cancel button (X) per item, calls `DELETE /api/scans/{id}`
- Empty state: "No scans queued"

**Step 3: Recently Completed section**

- Table: Course, Score (color-coded), Issues, When (relative time)
- Rows clickable to view full results
- Limited to last 10, "View All" links to History view

**Step 4: Auto-refresh**

- Poll `/api/scans` every 3 seconds (fallback for when WS disconnects)
- WebSocket updates are immediate for active scans

**Step 5: Commit**

```bash
git add src/a11yscope/web/static/app.js src/a11yscope/web/static/index.html
git commit -m "feat: add dashboard content — active scans, queue, recent completions"
```

---

## Task 11: Frontend — Scan Detail View

**Rationale:** The drill-down view when clicking an active or completed scan. Shows phase stepper, live feed, running stats.

**Files:**
- Modify: `src/a11yscope/web/static/app.js`
- Modify: `src/a11yscope/web/static/index.html`

**Step 1: Phase stepper**

- 4 steps: Fetching → Checking → Files → Scoring
- Each shows done (checkmark), active (spinner), or pending (circle) state
- Driven by WebSocket `phase` messages

**Step 2: Live feed**

- Scrollable list of content items
- Icons: checkmark (done), spinner (active), circle (pending)
- Issue count per completed item
- Auto-scrolls to active item
- Populated from WebSocket `item_start` and `item_done` messages

**Step 3: Running stats bar**

- Items: 18/26 | Issues: 12 | Files: 0/8
- Updated on each `stats` WebSocket message

**Step 4: Completed scan view**

- When scan is complete, show score gauge + issues table + fix/report buttons
- Reuse existing results rendering logic from the wizard Step 4/5/6

**Step 5: Commit**

```bash
git add src/a11yscope/web/static/app.js src/a11yscope/web/static/index.html
git commit -m "feat: add scan detail view with live feed and phase stepper"
```

---

## Task 12: Frontend — New Scan Modal & API Keys View

**Rationale:** The modal for starting new scans and the keys management view.

**Files:**
- Modify: `src/a11yscope/web/static/app.js`
- Modify: `src/a11yscope/web/static/index.html`

**Step 1: New Scan modal**

- API key dropdown (populated from `/api/keys`)
- "Add New Key" inline form option
- Course list (fetched from `/api/keys/{id}/courses`)
- Multi-select checkboxes with search filter
- "Select All" toggle
- "Start N Scans" button → `POST /api/scans`
- Previously scanned courses show last score badge

**Step 2: API Keys view**

- List of saved keys as cards
- Each shows: name, Canvas URL, course count, last used, masked token
- Delete button with confirmation
- "+ Add Key" form: name, Canvas URL, token input
- Token input is `type="password"` (masked by default)

**Step 3: Courses endpoint**

Add to `src/a11yscope/web/api/key_routes.py`:

```python
@router.get("/keys/{key_id}/courses")
async def list_courses_for_key(
    key_id: str,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Fetch available courses for a saved API key."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id)
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")

    settings = get_settings()
    token = decrypt_token(key.encrypted_token, settings.effective_secret_key)

    from a11yscope.canvas.client import CanvasClient
    async with CanvasClient(key.canvas_url, token) as client:
        courses = await client.get_courses()

    # Update cached course count
    key.course_count = len(courses)
    key.last_used_at = datetime.now(timezone.utc)
    await db.commit()

    return [{"id": c["id"], "name": c["name"], "code": c.get("course_code", "")} for c in courses]
```

**Step 4: Commit**

```bash
git add src/a11yscope/web/static/ src/a11yscope/web/api/key_routes.py
git commit -m "feat: add new scan modal, API keys view, and courses endpoint"
```

---

## Task 13: Wire Up Queue Manager to Audit Runner

**Rationale:** Connect the ScanQueueManager to the actual audit_runner so scans execute with item-level progress, DB persistence, and checkpointing.

**Files:**
- Modify: `src/a11yscope/web/queue_manager.py` (implement `_execute_job`)
- Modify: `src/a11yscope/web/audit_runner.py` (add item-level callbacks)
- Test: `tests/test_queue_execution.py`

**Step 1: Update audit_runner to emit item-level messages**

Add `item_start` and `item_done` message types to the existing progress callback pattern. Add `stats` summary messages after each item.

**Step 2: Implement `_execute_job` in queue_manager**

- Decrypt the API key
- Call `run_audit()` with a progress callback that:
  - Appends to `job.progress_log`
  - Updates `job.progress_pct`, `job.current_phase`, `job.current_item`
  - Persists checkpoint to DB after each item
- On completion: save `result_json` to DB
- On failure: save error to DB, set status to `failed`

**Step 3: Add checkpoint persistence**

After each `item_done`, update `audit_jobs.checkpoint_json`:
```json
{"last_completed_index": 17, "phase": "checking"}
```

**Step 4: Test end-to-end with mock Canvas client**

```python
# tests/test_queue_execution.py
# Integration test with mocked Canvas API
```

**Step 5: Commit**

```bash
git add src/a11yscope/web/queue_manager.py src/a11yscope/web/audit_runner.py tests/test_queue_execution.py
git commit -m "feat: wire queue manager to audit runner with item-level progress"
```

---

## Task 14: CORS Hardening & Rate Limiting

**Rationale:** The current CORS config is `allow_origins=["*"]` which is too permissive. Add rate limiting to prevent abuse (CWE-770).

**Files:**
- Modify: `src/a11yscope/web/app.py` (CORS config)
- Create: `src/a11yscope/web/middleware/rate_limit.py`
- Modify: `src/a11yscope/config.py` (add CORS settings)
- Test: `tests/test_rate_limit.py`

**Step 1: Tighten CORS**

Replace `allow_origins=["*"]` with configurable origins:

```python
# config.py
cors_origins: str = ""  # comma-separated, empty = same-origin only
```

**Step 2: Add rate limiter**

Simple in-memory sliding window rate limiter:
- 10 scan starts per minute per user
- 100 API calls per minute per user
- Returns 429 with `Retry-After` header when exceeded

**Step 3: Test**

```python
# tests/test_rate_limit.py
```

**Step 4: Commit**

```bash
git add src/a11yscope/web/app.py src/a11yscope/web/middleware/rate_limit.py \
        src/a11yscope/config.py tests/test_rate_limit.py
git commit -m "feat: harden CORS and add rate limiting (CWE-770)"
```

---

## Task 15: Integration Testing & Security Verification

**Rationale:** End-to-end tests validating the full flow: save key → start scan → monitor progress → view results. Plus security-specific tests.

**Files:**
- Create: `tests/test_integration_dashboard.py`
- Create: `tests/test_security_audit.py`

**Step 1: Integration test**

```python
# Full flow: create key → create scan → poll status → verify completion
```

**Step 2: Security audit tests**

```python
# tests/test_security_audit.py
# - Verify no plaintext tokens in any API response
# - Verify user A cannot see user B's keys or scans
# - Verify HTTPS-only Canvas URL enforcement
# - Verify CSP header on all responses
# - Verify rate limiting triggers at threshold
# - Verify WebSocket rejects unauthenticated connections
```

**Step 3: Run full test suite**

Run: `cd ~/Canvas-accessibility-buddy && python -m pytest tests/ -v --tb=short`

**Step 4: Commit**

```bash
git add tests/test_integration_dashboard.py tests/test_security_audit.py
git commit -m "test: add integration and security audit tests"
```

---

## Task 16: Final Cleanup & Push

**Step 1: Run bandit security scan**

```bash
cd ~/Canvas-accessibility-buddy && pip install bandit && bandit -r src/ -ll
```
Fix any medium/high findings.

**Step 2: Run full test suite**

```bash
python -m pytest tests/ -v
```

**Step 3: Update pyproject.toml**

Add new dependencies if needed (cryptography should already be available).

**Step 4: Push**

```bash
git push origin main
```
