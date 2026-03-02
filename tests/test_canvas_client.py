"""Tests for the Canvas LMS API client.

Covers:
- _parse_next_link: extracting 'next' URL from Link headers
- CanvasClient construction and configuration
- CanvasAPIError exception structure
"""
import pytest

from canvas_a11y.canvas.client import CanvasClient, CanvasAPIError


# ---------------------------------------------------------------------------
# _parse_next_link (static method -- no network needed)
# ---------------------------------------------------------------------------
class TestParseNextLink:
    def test_parses_next_link(self):
        header = (
            '<https://canvas.example.com/api/v1/courses?page=2>; rel="next", '
            '<https://canvas.example.com/api/v1/courses?page=1>; rel="prev"'
        )
        result = CanvasClient._parse_next_link(header)
        assert result == "https://canvas.example.com/api/v1/courses?page=2"

    def test_returns_none_no_next(self):
        header = '<https://canvas.example.com/api/v1/courses?page=1>; rel="prev"'
        result = CanvasClient._parse_next_link(header)
        assert result is None

    def test_returns_none_empty_string(self):
        assert CanvasClient._parse_next_link("") is None

    def test_next_only(self):
        header = '<https://canvas.example.com/api/v1/courses?page=3>; rel="next"'
        result = CanvasClient._parse_next_link(header)
        assert result == "https://canvas.example.com/api/v1/courses?page=3"

    def test_multiple_rels_next_first(self):
        header = (
            '<https://canvas.example.com/api/v1/courses?page=2>; rel="next", '
            '<https://canvas.example.com/api/v1/courses?page=5>; rel="last", '
            '<https://canvas.example.com/api/v1/courses?page=1>; rel="first"'
        )
        result = CanvasClient._parse_next_link(header)
        assert result == "https://canvas.example.com/api/v1/courses?page=2"

    def test_next_in_middle(self):
        header = (
            '<https://canvas.example.com/api/v1/courses?page=1>; rel="prev", '
            '<https://canvas.example.com/api/v1/courses?page=3>; rel="next", '
            '<https://canvas.example.com/api/v1/courses?page=10>; rel="last"'
        )
        result = CanvasClient._parse_next_link(header)
        assert result == "https://canvas.example.com/api/v1/courses?page=3"

    def test_complex_url_with_params(self):
        header = '<https://canvas.example.com/api/v1/courses?page=2&per_page=100&enrollment_type=teacher>; rel="next"'
        result = CanvasClient._parse_next_link(header)
        assert "page=2" in result
        assert "per_page=100" in result

    def test_only_last_and_first(self):
        header = (
            '<https://canvas.example.com/api/v1/courses?page=1>; rel="first", '
            '<https://canvas.example.com/api/v1/courses?page=5>; rel="last"'
        )
        result = CanvasClient._parse_next_link(header)
        assert result is None


# ---------------------------------------------------------------------------
# CanvasClient construction
# ---------------------------------------------------------------------------
class TestCanvasClientInit:
    def test_base_url_trailing_slash_stripped(self):
        client = CanvasClient("https://canvas.example.com/", "fake-token")
        assert client.base_url == "https://canvas.example.com"

    def test_api_url_constructed(self):
        client = CanvasClient("https://canvas.example.com", "fake-token")
        assert client.api_url == "https://canvas.example.com/api/v1"

    def test_custom_rate_limit_delay(self):
        client = CanvasClient("https://canvas.example.com", "fake-token", rate_limit_delay=0.5)
        assert client.rate_limit_delay == 0.5

    def test_default_rate_limit_delay(self):
        client = CanvasClient("https://canvas.example.com", "fake-token")
        assert client.rate_limit_delay == 0.25


# ---------------------------------------------------------------------------
# CanvasAPIError
# ---------------------------------------------------------------------------
class TestCanvasAPIError:
    def test_error_attributes(self):
        err = CanvasAPIError(404, "Not Found")
        assert err.status_code == 404
        assert err.message == "Not Found"

    def test_error_string(self):
        err = CanvasAPIError(403, "Forbidden")
        assert "403" in str(err)
        assert "Forbidden" in str(err)

    def test_inherits_from_exception(self):
        err = CanvasAPIError(500, "Internal Server Error")
        assert isinstance(err, Exception)

    def test_can_be_raised_and_caught(self):
        with pytest.raises(CanvasAPIError) as exc_info:
            raise CanvasAPIError(429, "Rate limited")
        assert exc_info.value.status_code == 429
