"""E2E: Security tests — OWASP-aligned checks."""
import pytest


@pytest.mark.asyncio
async def test_no_credentials_in_status_response(client):
    """Config status endpoint must never leak API tokens."""
    resp = await client.get("/api/config/status")
    data = resp.json()
    # Must not contain token fields
    assert "canvas_api_token" not in data
    assert "anthropic_api_key" not in data
    assert "api_token" not in data
    text = resp.text.lower()
    assert "bearer" not in text


@pytest.mark.asyncio
async def test_no_directory_traversal_static(client):
    """Static file serving must not allow path traversal."""
    traversal_paths = [
        "/static/../pyproject.toml",
        "/static/../../etc/passwd",
        "/static/%2e%2e/pyproject.toml",
        "/static/..%2fpyproject.toml",
    ]
    for path in traversal_paths:
        resp = await client.get(path)
        # Should be 404 or 400, never 200 with file contents
        if resp.status_code == 200:
            assert "[build-system]" not in resp.text, f"Path traversal succeeded: {path}"
            assert "root:" not in resp.text, f"Path traversal succeeded: {path}"


@pytest.mark.asyncio
async def test_xss_in_config_input(client):
    """Config endpoint must not reflect script tags."""
    resp = await client.post("/api/config", json={
        "canvas_base_url": "<script>alert('xss')</script>",
        "canvas_api_token": "<img onerror=alert(1) src=x>",
    })
    # The response should be JSON, not reflected HTML
    assert resp.headers.get("content-type", "").startswith("application/json")
    # Response should not contain raw script tags
    assert "<script>" not in resp.text


@pytest.mark.asyncio
async def test_cors_headers_not_wildcard(client):
    """CORS should not allow wildcard origin for API routes."""
    resp = await client.get("/api/config/status")
    cors = resp.headers.get("access-control-allow-origin", "")
    assert cors != "*", "CORS wildcard origin is insecure"


@pytest.mark.asyncio
async def test_json_content_type_on_api(client):
    """API endpoints must return application/json content type."""
    endpoints = [
        "/api/config/status",
        "/health",
    ]
    for ep in endpoints:
        resp = await client.get(ep)
        ct = resp.headers.get("content-type", "")
        assert "json" in ct, f"Non-JSON content type on {ep}: {ct}"


@pytest.mark.asyncio
async def test_sql_injection_in_job_id(client):
    """Job IDs with SQL injection attempts must return 404, not 500."""
    payloads = [
        "' OR '1'='1",
        "1; DROP TABLE users;--",
        "' UNION SELECT * FROM sessions--",
    ]
    for payload in payloads:
        resp = await client.get(f"/api/audit/{payload}")
        assert resp.status_code in (404, 422), f"Unexpected {resp.status_code} for SQLi payload"


@pytest.mark.asyncio
async def test_large_payload_rejection(client):
    """Extremely large payloads should be rejected gracefully."""
    # 1MB of garbage in the token field
    big_token = "x" * (1024 * 1024)
    resp = await client.post("/api/config", json={
        "canvas_base_url": "https://canvas.jccc.edu",
        "canvas_api_token": big_token,
    })
    # Should not crash the server — either 200 (handled) or 413/422
    assert resp.status_code in (200, 413, 422)
