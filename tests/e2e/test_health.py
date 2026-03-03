"""E2E: Health and basic endpoint tests."""
import pytest


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """GET /health returns 200 with ok status."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_index_serves_html(client):
    """GET / returns the SPA index.html."""
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "A11yScope" in resp.text


@pytest.mark.asyncio
async def test_static_js_served(client):
    """GET /static/app.js returns the Alpine.js application."""
    resp = await client.get("/static/app.js")
    assert resp.status_code == 200
    assert "auditApp" in resp.text


@pytest.mark.asyncio
async def test_config_status_default(client):
    """GET /api/config/status returns not-validated by default."""
    resp = await client.get("/api/config/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["validated"] is False


@pytest.mark.asyncio
async def test_courses_requires_auth(client):
    """GET /api/courses returns 401 without credentials."""
    resp = await client.get("/api/courses")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_audit_requires_auth(client):
    """POST /api/audit returns 401 without credentials."""
    resp = await client.post("/api/audit", json={"course_id": 1})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_report_404_missing_job(client):
    """GET /api/report/nonexistent/html returns 404."""
    resp = await client.get("/api/report/nonexistent/html")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_fix_404_missing_job(client):
    """POST /api/fix/nonexistent returns 404."""
    resp = await client.post("/api/fix/nonexistent", json={})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_audit_status_404_missing_job(client):
    """GET /api/audit/nonexistent returns 404."""
    resp = await client.get("/api/audit/nonexistent")
    assert resp.status_code == 404
