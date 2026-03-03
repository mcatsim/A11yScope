"""In-memory sliding window rate limiter (CWE-770)."""

from __future__ import annotations

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimiter:
    """Simple sliding window rate limiter."""

    def __init__(self, max_requests: int, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        window_start = now - self.window
        # Clean old entries
        self._hits[key] = [t for t in self._hits[key] if t > window_start]
        if len(self._hits[key]) >= self.max_requests:
            return False
        self._hits[key].append(now)
        return True


# Global limiters
_api_limiter = RateLimiter(max_requests=100, window_seconds=60)
_scan_limiter = RateLimiter(max_requests=10, window_seconds=60)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limit API requests per client IP."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path

        # Only rate-limit /api/ paths
        if not path.startswith("/api/"):
            return await call_next(request)

        # Get user identifier (IP address as fallback)
        user_key = request.client.host if request.client else "unknown"

        # Check scan-specific limit
        if path == "/api/scans" and request.method == "POST":
            if not _scan_limiter.is_allowed(f"scan:{user_key}"):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded for scan creation"},
                    headers={"Retry-After": "60"},
                )

        # Check general API limit
        if not _api_limiter.is_allowed(f"api:{user_key}"):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": "60"},
            )

        return await call_next(request)
