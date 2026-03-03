# tests/test_security_audit.py
"""Security audit tests -- validates defense-in-depth controls.

Validates:
- No plaintext tokens leak in API responses (CWE-312)
- User isolation: User A cannot see User B's keys (CWE-639)
- HTTPS-only Canvas URLs (CWE-918 / SSRF prevention)
- Content-Security-Policy on all responses (CWE-79)
- Security headers on API responses (X-Content-Type-Options, X-Frame-Options)
- Cache-Control: no-store on sensitive endpoints
- User isolation for scans (CWE-639)
"""
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient, ASGITransport

from a11yscope.web.app import app
from a11yscope.auth.backend import AuthUser
from a11yscope.auth.dependencies import get_current_user
from a11yscope.db.models import Base
from a11yscope.db.session import get_db
from a11yscope.web.queue_manager import ScanQueueManager, QueuedJob
from a11yscope.web.api.scan_routes import set_queue_manager

USER_A = AuthUser(id="user-a", email="a@test.com", display_name="A", role="auditor")
USER_B = AuthUser(id="user-b", email="b@test.com", display_name="B", role="auditor")


@pytest.fixture
async def test_db():
    """Create an in-memory SQLite database with all tables."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.fixture
def auth_user_a(test_db):
    """Override auth as User A with in-memory DB."""
    async def _get_db():
        async with test_db() as session:
            yield session

    qm = ScanQueueManager()
    app.dependency_overrides[get_current_user] = lambda: USER_A
    app.dependency_overrides[get_db] = _get_db
    set_queue_manager(qm)
    yield
    app.dependency_overrides.clear()
    set_queue_manager(None)


@pytest.fixture
def multi_user_db(test_db):
    """Override DB for multi-user tests. Auth is switched inline."""
    async def _get_db():
        async with test_db() as session:
            yield session

    qm = ScanQueueManager()
    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_current_user] = lambda: USER_A
    set_queue_manager(qm)
    yield qm
    app.dependency_overrides.clear()
    set_queue_manager(None)


# ---------- Token secrecy (CWE-312) ----------


@pytest.mark.asyncio
async def test_no_plaintext_tokens_in_key_response(auth_user_a):
    """API key responses must never contain plaintext tokens."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/keys", json={
            "name": "Test Key",
            "canvas_url": "https://canvas.test.edu",
            "token": "super-secret-token-abcdefghij",
        })
    assert resp.status_code == 201
    data = resp.json()
    # The plaintext token must never appear anywhere in the response
    assert "super-secret-token" not in str(data)
    assert "encrypted_token" not in data
    assert data["token_hint"] == "ghij"


@pytest.mark.asyncio
async def test_no_plaintext_tokens_in_list_response(auth_user_a):
    """List keys response must never contain plaintext tokens."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/keys", json={
            "name": "Listed Key",
            "canvas_url": "https://canvas.list.edu",
            "token": "my-very-secret-token-12345678",
        })
        resp = await client.get("/api/keys")
    assert resp.status_code == 200
    raw = str(resp.json())
    assert "my-very-secret-token" not in raw
    assert "encrypted_token" not in raw


# ---------- User isolation (CWE-639 / IDOR) ----------


@pytest.mark.asyncio
async def test_user_isolation_keys(multi_user_db):
    """User A cannot see User B's keys."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # User A creates a key
        app.dependency_overrides[get_current_user] = lambda: USER_A
        create_resp = await client.post("/api/keys", json={
            "name": "Key for User A",
            "canvas_url": "https://a.edu",
            "token": "token-for-user-a-abcdefghij",
        })
        assert create_resp.status_code == 201

        # User B lists keys -- should not see A's key
        app.dependency_overrides[get_current_user] = lambda: USER_B
        resp = await client.get("/api/keys")
    keys = resp.json()
    assert all(k["name"] != "Key for User A" for k in keys)


@pytest.mark.asyncio
async def test_user_isolation_key_delete(multi_user_db):
    """User B cannot delete User A's key."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # User A creates a key
        app.dependency_overrides[get_current_user] = lambda: USER_A
        create_resp = await client.post("/api/keys", json={
            "name": "Protected Key",
            "canvas_url": "https://a-protected.edu",
            "token": "token-for-user-a-xyzw123456",
        })
        key_id = create_resp.json()["id"]

        # User B tries to delete it -- should get 404
        app.dependency_overrides[get_current_user] = lambda: USER_B
        del_resp = await client.delete(f"/api/keys/{key_id}")
    assert del_resp.status_code == 404


@pytest.mark.asyncio
async def test_user_isolation_scans(multi_user_db):
    """User A cannot see User B's scans.

    Uses pre-populated queue manager jobs to avoid background worker tasks.
    """
    qm = multi_user_db
    transport = ASGITransport(app=app)

    # Pre-populate a scan job for User A
    job = QueuedJob(
        job_id="user-a-scan",
        user_id=USER_A.id,
        api_key_id="fake-key-a",
        canvas_url="https://a-scan.edu",
        course_id=101,
        course_name="A's Course",
        status="queued",
    )
    qm._jobs["user-a-scan"] = job

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # User B lists scans -- should not see A's scans
        app.dependency_overrides[get_current_user] = lambda: USER_B
        list_resp = await client.get("/api/scans")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 0


@pytest.mark.asyncio
async def test_user_isolation_scan_detail(multi_user_db):
    """User B cannot get detail for User A's scan."""
    qm = multi_user_db
    transport = ASGITransport(app=app)

    # Pre-populate a scan job for User A
    job = QueuedJob(
        job_id="user-a-detail",
        user_id=USER_A.id,
        api_key_id="fake-key-a",
        canvas_url="https://a-detail.edu",
        course_id=202,
        course_name="A's Detail Course",
        status="running",
    )
    qm._jobs["user-a-detail"] = job

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # User B tries to view it -- should get 404
        app.dependency_overrides[get_current_user] = lambda: USER_B
        detail_resp = await client.get("/api/scans/user-a-detail")
    assert detail_resp.status_code == 404


@pytest.mark.asyncio
async def test_user_isolation_scan_cancel(multi_user_db):
    """User B cannot cancel User A's scan."""
    qm = multi_user_db
    transport = ASGITransport(app=app)

    # Pre-populate a scan job for User A
    job = QueuedJob(
        job_id="user-a-cancel",
        user_id=USER_A.id,
        api_key_id="fake-key-a",
        canvas_url="https://a-cancel.edu",
        course_id=303,
        course_name="A's Cancel Course",
        status="queued",
    )
    qm._jobs["user-a-cancel"] = job

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # User B tries to cancel it -- should get 404
        app.dependency_overrides[get_current_user] = lambda: USER_B
        cancel_resp = await client.delete("/api/scans/user-a-cancel")
    assert cancel_resp.status_code == 404


# ---------- Input validation ----------


@pytest.mark.asyncio
async def test_https_only_canvas_url(auth_user_a):
    """Canvas URL must be HTTPS (CWE-918 / SSRF prevention)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/keys", json={
            "name": "Bad Key",
            "canvas_url": "http://canvas.test.edu",
            "token": "token-at-least-twenty-chars",
        })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_token_minimum_length(auth_user_a):
    """Token must be at least 20 characters."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/keys", json={
            "name": "Short Token",
            "canvas_url": "https://canvas.test.edu",
            "token": "tooshort",
        })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_xss_in_key_name_rejected(auth_user_a):
    """Key name with script tags must be rejected (XSS prevention)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/keys", json={
            "name": '<script>alert("xss")</script>',
            "canvas_url": "https://canvas.test.edu",
            "token": "token-at-least-twenty-chars",
        })
    assert resp.status_code == 422


# ---------- Security headers ----------


@pytest.mark.asyncio
async def test_csp_on_all_responses():
    """Every response must have Content-Security-Policy."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert "Content-Security-Policy" in resp.headers
    csp = resp.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp


@pytest.mark.asyncio
async def test_security_headers_on_api_responses(auth_user_a):
    """API responses must have security headers including no-store for keys."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/keys")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers.get("Cache-Control") == "no-store"


@pytest.mark.asyncio
async def test_no_cache_on_scan_endpoints(auth_user_a):
    """Scan endpoints must have Cache-Control: no-store."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/scans")
    assert resp.headers.get("Cache-Control") == "no-store"


@pytest.mark.asyncio
async def test_health_endpoint_no_auth_required():
    """Health endpoint must be accessible without authentication."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_permissions_policy_header():
    """Permissions-Policy must restrict camera, mic, geolocation."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    pp = resp.headers.get("Permissions-Policy", "")
    assert "camera=()" in pp
    assert "microphone=()" in pp
    assert "geolocation=()" in pp


@pytest.mark.asyncio
async def test_referrer_policy_header():
    """Referrer-Policy must be strict-origin-when-cross-origin."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
