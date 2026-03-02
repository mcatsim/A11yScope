"""E2E tests for AI API routes."""
from __future__ import annotations
import pytest
from httpx import AsyncClient, ASGITransport
from accessiflow.web.app import app


@pytest.mark.asyncio
async def test_list_ai_providers():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/ai/providers")
        assert resp.status_code == 200
        providers = resp.json()
        assert len(providers) == 4
        ids = {p["id"] for p in providers}
        assert ids == {"anthropic", "openai", "google", "grok"}


@pytest.mark.asyncio
async def test_ai_config_status_unconfigured():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/ai/config/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["configured"] is False


@pytest.mark.asyncio
async def test_suggest_without_ai_config():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/ai/suggest/fake-job", json={"issue_index": 0})
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_suggest_batch_without_ai_config():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/ai/suggest-batch/fake-job")
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_configure_ai_invalid_provider():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/ai/config", json={
            "provider": "nonexistent", "api_key": "test-key",
        })
        assert resp.status_code == 400
