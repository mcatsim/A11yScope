"""Tests for the in-memory sliding window rate limiter."""

from __future__ import annotations

from a11yscope.web.middleware.rate_limit import RateLimiter


def test_allows_under_limit() -> None:
    limiter = RateLimiter(max_requests=3, window_seconds=60)
    assert limiter.is_allowed("user1") is True
    assert limiter.is_allowed("user1") is True
    assert limiter.is_allowed("user1") is True


def test_blocks_over_limit() -> None:
    limiter = RateLimiter(max_requests=2, window_seconds=60)
    assert limiter.is_allowed("user1") is True
    assert limiter.is_allowed("user1") is True
    assert limiter.is_allowed("user1") is False


def test_different_keys_independent() -> None:
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    assert limiter.is_allowed("user1") is True
    assert limiter.is_allowed("user2") is True
    assert limiter.is_allowed("user1") is False
