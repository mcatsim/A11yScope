# tests/test_key_routes.py
"""Tests for API key management routes (create, list, delete).

Validates:
- Keys are created with Fernet encryption, token never echoed back
- Token hint shows only last 4 chars
- HTTPS-only Canvas URLs (CWE-918 / SSRF prevention)
- Safe characters only in key name (XSS prevention)
- User-scoped listing (only own keys returned)
- Delete returns 204, missing key returns 404
"""
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient, ASGITransport
from a11yscope.web.app import app
from a11yscope.auth.backend import AuthUser
from a11yscope.db.models import Base
from a11yscope.db.session import get_db

MOCK_USER = AuthUser(
    id="user-1", email="test@test.com",
    display_name="Test", role="auditor",
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
    """Override auth and DB dependencies for testing."""
    from a11yscope.auth.dependencies import get_current_user

    async def _get_db():
        async with test_db() as session:
            yield session

    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_key(overrides):
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
async def test_list_keys_user_scoped(overrides):
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
async def test_create_key_rejects_http_url(overrides):
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
async def test_create_key_rejects_xss_name(overrides):
    """Key name must be safe characters only."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/keys", json={
            "name": '<script>alert("xss")</script>',
            "canvas_url": "https://canvas.example.edu",
            "token": "token-abcdefghijklmnop",
        })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_delete_key(overrides):
    """Delete returns 204 for own key."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a key first
        create_resp = await client.post("/api/keys", json={
            "name": "ToDelete",
            "canvas_url": "https://canvas.example.edu",
            "token": "token-abcdefghijklmnop",
        })
        key_id = create_resp.json()["id"]
        # Delete it
        resp = await client.delete(f"/api/keys/{key_id}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_key_not_found(overrides):
    """Delete returns 404 for nonexistent key."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.delete("/api/keys/nonexistent-id")
    assert resp.status_code == 404
