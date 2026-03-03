# tests/test_scan_routes.py
"""Tests for scan management routes (create, list, cancel).

Validates:
- Missing key_id returns 422
- Empty course_ids returns 422 (min_length=1)
- Duplicate course_ids returns 422
- List scans returns 200 with empty list when no scans exist
"""
import pytest
from httpx import AsyncClient, ASGITransport
from a11yscope.web.app import app
from a11yscope.auth.backend import AuthUser

MOCK_USER = AuthUser(id="u1", email="t@t.com", display_name="T", role="auditor")


@pytest.fixture
def auth_override():
    from a11yscope.auth.dependencies import get_current_user
    from a11yscope.web.queue_manager import ScanQueueManager
    from a11yscope.web.api.scan_routes import set_queue_manager

    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    # Initialize queue manager for tests (lifespan doesn't run with ASGITransport)
    qm = ScanQueueManager()
    set_queue_manager(qm)
    yield
    app.dependency_overrides.clear()
    set_queue_manager(None)


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
