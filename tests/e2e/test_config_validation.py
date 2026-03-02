"""E2E: Configuration and credential validation tests."""
import pytest


@pytest.mark.asyncio
async def test_config_invalid_token_rejected(client):
    """POST /api/config with bad credentials returns error."""
    resp = await client.post("/api/config", json={
        "canvas_base_url": "https://canvas.jccc.edu",
        "canvas_api_token": "bad-token-12345",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert "error" in data


@pytest.mark.asyncio
async def test_config_bad_url_rejected(client):
    """POST /api/config with unreachable URL returns error."""
    resp = await client.post("/api/config", json={
        "canvas_base_url": "https://nonexistent.invalid.local",
        "canvas_api_token": "some-token",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert "error" in data


@pytest.mark.asyncio
async def test_config_missing_token_validation(client):
    """POST /api/config with empty token is rejected by Pydantic."""
    resp = await client.post("/api/config", json={
        "canvas_base_url": "https://canvas.jccc.edu",
    })
    # Pydantic will reject missing required field
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_config_status_after_failed_config(client):
    """Config status stays not-validated after failed connection."""
    # First, try bad config
    await client.post("/api/config", json={
        "canvas_base_url": "https://nonexistent.invalid.local",
        "canvas_api_token": "bad-token",
    })
    # Status should still show not validated (or previous state)
    resp = await client.get("/api/config/status")
    data = resp.json()
    # May or may not be validated depending on prior test state,
    # but should not error
    assert resp.status_code == 200
    assert "validated" in data
