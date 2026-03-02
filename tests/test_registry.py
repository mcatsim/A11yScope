"""Tests for the pluggable check registry.

Covers:
- @register_check decorator
- get_all_checks: returns instances of all registered checks
- get_check_by_id: lookup by ID, missing ID returns None
- All 14 checks (13 HTML + 1 contrast) are registered
"""
import pytest

from accessiflow.checks.registry import get_all_checks, get_check_by_id
from accessiflow.checks.base import AccessibilityCheck


# Ensure all check modules are imported (they register on import)
import accessiflow.checks.html_checks  # noqa: F401
import accessiflow.checks.contrast_check  # noqa: F401


ALL_CHECK_IDS = [
    "alt-text-missing",
    "alt-text-nondescriptive",
    "heading-hierarchy",
    "link-text-nondescriptive",
    "table-missing-headers",
    "table-missing-caption",
    "table-header-missing-scope",
    "empty-link",
    "empty-button",
    "iframe-missing-title",
    "media-missing-captions",
    "form-input-missing-label",
    "deprecated-elements",
    "color-contrast",
]


class TestGetAllChecks:
    def test_returns_list(self):
        checks = get_all_checks()
        assert isinstance(checks, list)

    def test_all_instances_of_base(self):
        for check in get_all_checks():
            assert isinstance(check, AccessibilityCheck)

    def test_returns_at_least_14_checks(self):
        """At minimum the 13 HTML checks + 1 contrast check should be registered."""
        checks = get_all_checks()
        assert len(checks) >= 14

    def test_each_check_has_check_id(self):
        for check in get_all_checks():
            assert check.check_id, f"Check {type(check).__name__} has empty check_id"

    def test_each_check_has_title(self):
        for check in get_all_checks():
            assert check.title, f"Check {type(check).__name__} has empty title"

    def test_each_check_has_wcag_criterion(self):
        for check in get_all_checks():
            assert check.wcag_criterion, f"Check {type(check).__name__} has empty wcag_criterion"

    def test_unique_check_ids(self):
        ids = [check.check_id for check in get_all_checks()]
        assert len(ids) == len(set(ids)), f"Duplicate check IDs: {ids}"

    def test_expected_ids_present(self):
        actual_ids = {check.check_id for check in get_all_checks()}
        for expected_id in ALL_CHECK_IDS:
            assert expected_id in actual_ids, f"Missing check: {expected_id}"


class TestGetCheckById:
    @pytest.mark.parametrize("check_id", ALL_CHECK_IDS)
    def test_finds_each_check(self, check_id):
        check = get_check_by_id(check_id)
        assert check is not None
        assert check.check_id == check_id

    def test_returns_none_for_unknown(self):
        assert get_check_by_id("nonexistent-check") is None

    def test_returns_none_for_empty_string(self):
        assert get_check_by_id("") is None

    def test_returned_check_has_check_html_method(self):
        check = get_check_by_id("alt-text-missing")
        assert hasattr(check, "check_html")
        assert callable(check.check_html)
