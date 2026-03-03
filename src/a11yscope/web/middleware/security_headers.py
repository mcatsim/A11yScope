"""Security headers middleware — hardens every HTTP response.

Mitigates:
- CWE-79  (XSS)          via Content-Security-Policy + X-Content-Type-Options
- CWE-693 (clickjacking)  via X-Frame-Options
- CWE-116 (MIME sniffing)  via X-Content-Type-Options
"""
from __future__ import annotations

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
