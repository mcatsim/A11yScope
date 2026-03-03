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
