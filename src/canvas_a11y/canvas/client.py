"""Async Canvas LMS API client with pagination and rate limiting."""
import asyncio
import re
from typing import Any

import httpx


class CanvasAPIError(Exception):
    """Raised when Canvas API returns an error."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Canvas API error {status_code}: {message}")


class CanvasClient:
    """Async client for Canvas LMS REST API."""

    def __init__(self, base_url: str, api_token: str, rate_limit_delay: float = 0.25, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}/api/v1"
        self.rate_limit_delay = rate_limit_delay
        self._client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {api_token}",
                "Accept": "application/json",
            },
            timeout=timeout,
            follow_redirects=True,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def close(self):
        await self._client.aclose()

    async def _request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        """Make a rate-limited request with retry on 429."""
        url = f"{self.api_url}/{endpoint.lstrip('/')}" if not endpoint.startswith("http") else endpoint

        for attempt in range(5):
            await asyncio.sleep(self.rate_limit_delay)
            response = await self._client.request(method, url, **kwargs)

            if response.status_code == 429:
                retry_after = float(response.headers.get("Retry-After", 2 ** attempt))
                await asyncio.sleep(retry_after)
                continue

            if response.status_code >= 400:
                raise CanvasAPIError(response.status_code, response.text)

            return response

        raise CanvasAPIError(429, "Rate limit exceeded after retries")

    async def get(self, endpoint: str, params: dict | None = None) -> Any:
        """GET request returning JSON."""
        response = await self._request("GET", endpoint, params=params)
        return response.json()

    async def get_paginated(self, endpoint: str, params: dict | None = None, per_page: int = 100) -> list[Any]:
        """GET with automatic Link header pagination. Returns all results."""
        params = {**(params or {}), "per_page": per_page}
        all_results = []
        url = f"{self.api_url}/{endpoint.lstrip('/')}"

        while url:
            await asyncio.sleep(self.rate_limit_delay)
            response = await self._client.get(url, params=params if not all_results else None)

            if response.status_code == 429:
                retry_after = float(response.headers.get("Retry-After", 2))
                await asyncio.sleep(retry_after)
                continue

            if response.status_code >= 400:
                raise CanvasAPIError(response.status_code, response.text)

            data = response.json()
            if isinstance(data, list):
                all_results.extend(data)
            else:
                all_results.append(data)

            # Parse Link header for next page
            url = self._parse_next_link(response.headers.get("Link", ""))
            params = None  # params are in the URL from Link header

        return all_results

    @staticmethod
    def _parse_next_link(link_header: str) -> str | None:
        """Extract 'next' URL from Link header."""
        if not link_header:
            return None
        for part in link_header.split(","):
            match = re.match(r'<([^>]+)>;\s*rel="next"', part.strip())
            if match:
                return match.group(1)
        return None

    async def put(self, endpoint: str, json: dict | None = None) -> Any:
        """PUT request returning JSON."""
        response = await self._request("PUT", endpoint, json=json)
        return response.json()

    async def post(self, endpoint: str, json: dict | None = None, data: dict | None = None, files: dict | None = None) -> Any:
        """POST request returning JSON."""
        response = await self._request("POST", endpoint, json=json, data=data, files=files)
        return response.json()

    async def download_file(self, url: str, dest: "Path") -> "Path":
        """Download a file from a URL to a local path."""
        from pathlib import Path
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)

        async with self._client.stream("GET", url) as response:
            if response.status_code >= 400:
                raise CanvasAPIError(response.status_code, f"Failed to download {url}")
            with open(dest, "wb") as f:
                async for chunk in response.aiter_bytes(8192):
                    f.write(chunk)
        return dest

    # Convenience methods for common Canvas endpoints
    async def get_course(self, course_id: int) -> dict:
        return await self.get(f"courses/{course_id}")

    async def get_courses(self) -> list[dict]:
        return await self.get_paginated("courses", params={"enrollment_type": "teacher", "state[]": "available"})
