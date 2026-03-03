# tests/test_integration_dashboard.py
"""Integration tests -- full scan dashboard flow.

Validates the end-to-end API flow:
1. Save an API key via POST /api/keys
2. List keys via GET /api/keys -- verify it appears
3. Start a scan via POST /api/scans -- verify queued
4. List scans via GET /api/scans -- verify it appears
5. Get scan detail via GET /api/scans/{id}
6. Cancel scan via DELETE /api/scans/{id}

Note: Tests that create scans pre-populate the queue manager's job
dict directly to avoid spawning background asyncio worker tasks that
interfere with pytest-asyncio event loop cleanup when other test
modules (e.g. litellm-based AI provider tests) are in the same run.
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

MOCK_USER = AuthUser(
    id="integration-user-1",
    email="integration@test.com",
    display_name="Integration Tester",
    role="auditor",
)


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
def overrides(test_db):
    """Override auth, DB, and queue manager dependencies for testing."""
    async def _get_db():
        async with test_db() as session:
            yield session

    qm = ScanQueueManager()
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    app.dependency_overrides[get_db] = _get_db
    set_queue_manager(qm)
    yield qm
    app.dependency_overrides.clear()
    set_queue_manager(None)


# ---------------------------------------------------------------------------
# Full flow integration test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_full_key_and_scan_flow(overrides):
    """End-to-end: save key -> list keys -> mock-enqueue scan -> list -> detail -> cancel."""
    qm = overrides
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # ---- Step 1: Save an API key ----
        create_key_resp = await client.post("/api/keys", json={
            "name": "Integration Canvas",
            "canvas_url": "https://canvas.integration.edu",
            "token": "integration-test-token-abcdefghij",
        })
        assert create_key_resp.status_code == 201, create_key_resp.text
        key_data = create_key_resp.json()
        assert key_data["name"] == "Integration Canvas"
        assert key_data["canvas_url"] == "https://canvas.integration.edu"
        assert key_data["token_hint"] == "ghij"
        key_id = key_data["id"]

        # ---- Step 2: List keys -- verify it appears ----
        list_keys_resp = await client.get("/api/keys")
        assert list_keys_resp.status_code == 200
        keys = list_keys_resp.json()
        assert len(keys) == 1
        assert keys[0]["id"] == key_id
        assert keys[0]["name"] == "Integration Canvas"
        # Token must never appear in list response
        assert "token" not in keys[0]
        assert "encrypted_token" not in keys[0]

        # ---- Step 3: Pre-populate scan jobs (avoids background worker tasks) ----
        job_1 = QueuedJob(
            job_id="int-job-1",
            user_id=MOCK_USER.id,
            api_key_id=key_id,
            canvas_url="https://canvas.integration.edu",
            course_id=101,
            course_name="Course 101",
            status="queued",
        )
        job_2 = QueuedJob(
            job_id="int-job-2",
            user_id=MOCK_USER.id,
            api_key_id=key_id,
            canvas_url="https://canvas.integration.edu",
            course_id=202,
            course_name="Course 202",
            status="running",
            progress_pct=50,
        )
        qm._jobs["int-job-1"] = job_1
        qm._jobs["int-job-2"] = job_2

        # ---- Step 4: List scans -- verify both appear ----
        list_scans_resp = await client.get("/api/scans")
        assert list_scans_resp.status_code == 200
        scan_list = list_scans_resp.json()
        scan_ids = {s["job_id"] for s in scan_list}
        assert "int-job-1" in scan_ids
        assert "int-job-2" in scan_ids

        # ---- Step 5: Get scan detail ----
        detail_resp = await client.get("/api/scans/int-job-1")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["job_id"] == "int-job-1"
        assert detail["course_id"] == 101
        assert detail["status"] == "queued"

        detail_resp_2 = await client.get("/api/scans/int-job-2")
        assert detail_resp_2.status_code == 200
        assert detail_resp_2.json()["progress_pct"] == 50

        # ---- Step 6: Cancel scan via API ----
        cancel_resp = await client.delete("/api/scans/int-job-1")
        assert cancel_resp.status_code == 204

        # Verify cancelled status
        detail_after = await client.get("/api/scans/int-job-1")
        assert detail_after.status_code == 200
        assert detail_after.json()["status"] == "cancelled"


# ---------------------------------------------------------------------------
# Edge cases and error paths
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scan_with_invalid_key_returns_404(overrides):
    """Starting a scan with a nonexistent key_id returns 404."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/scans", json={
            "key_id": "nonexistent-key-id",
            "course_ids": [101],
        })
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cancel_nonexistent_scan_returns_404(overrides):
    """Cancelling a nonexistent scan returns 404."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.delete("/api/scans/nonexistent-job-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_nonexistent_scan_returns_404(overrides):
    """Getting a nonexistent scan returns 404."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/scans/nonexistent-job-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_key_then_list_empty(overrides):
    """After deleting a key, the list should be empty."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a key
        create_resp = await client.post("/api/keys", json={
            "name": "Temp Key",
            "canvas_url": "https://canvas.temp.edu",
            "token": "temporary-token-abcdefghij",
        })
        key_id = create_resp.json()["id"]

        # Delete it
        del_resp = await client.delete(f"/api/keys/{key_id}")
        assert del_resp.status_code == 204

        # List should be empty
        list_resp = await client.get("/api/keys")
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 0


@pytest.mark.asyncio
async def test_create_multiple_keys_then_list(overrides):
    """Creating multiple keys should all appear in the list."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for i in range(3):
            await client.post("/api/keys", json={
                "name": f"Key {i}",
                "canvas_url": f"https://canvas{i}.edu",
                "token": f"token-for-key-{i}-abcdefgh",
            })

        list_resp = await client.get("/api/keys")
        assert list_resp.status_code == 200
        keys = list_resp.json()
        assert len(keys) == 3
        names = {k["name"] for k in keys}
        assert names == {"Key 0", "Key 1", "Key 2"}
