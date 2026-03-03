"""Tests for VPAT report generation."""
from __future__ import annotations

import pytest
from datetime import datetime
from pathlib import Path

from a11yscope.models import (
    CourseAuditResult, ContentItem, ContentType,
    AccessibilityIssue, Severity,
)
from a11yscope.standards.vpat import build_vpat, VPATReport, VPATRow
from a11yscope.reporting.vpat_report import generate_vpat_report


def _make_result(issues=None):
    """Helper to create a CourseAuditResult with given issues."""
    items = []
    if issues:
        items.append(ContentItem(
            id=1, content_type=ContentType.PAGE,
            title="Test Page", url="http://test/page",
            html_content="<p>test</p>",
            issues=issues,
        ))
    return CourseAuditResult(
        course_id=1, course_name="Test Course",
        audit_timestamp=datetime.now(),
        content_items=items,
    )


def test_vpat_empty_result():
    """A clean course should mostly show Supports or Not Evaluated."""
    result = _make_result()
    vpat = build_vpat(result)
    assert isinstance(vpat, VPATReport)
    assert vpat.supports_count >= 0
    assert vpat.does_not_support_count == 0


def test_vpat_with_critical_issues():
    """Critical issues should produce 'Does Not Support'."""
    issues = [
        AccessibilityIssue(
            check_id="alt-text-missing",
            title="Image missing alt text",
            description="Test",
            severity=Severity.CRITICAL,
            wcag_criterion="1.1.1",
        ),
    ]
    result = _make_result(issues)
    vpat = build_vpat(result)

    # WCAG 1.1.1 should be "Does Not Support"
    row_111 = next((r for r in vpat.rows if r.criterion_id == "1.1.1"), None)
    assert row_111 is not None
    assert row_111.level == "Does Not Support"


def test_vpat_with_minor_issues():
    """Minor issues should produce 'Partially Supports'."""
    issues = [
        AccessibilityIssue(
            check_id="heading-hierarchy",
            title="Heading hierarchy skip",
            description="Test",
            severity=Severity.MINOR,
            wcag_criterion="1.3.1",
        ),
    ]
    result = _make_result(issues)
    vpat = build_vpat(result)

    row_131 = next((r for r in vpat.rows if r.criterion_id == "1.3.1"), None)
    assert row_131 is not None
    assert row_131.level == "Partially Supports"


def test_vpat_report_generation(tmp_path):
    """Test HTML report file is generated."""
    result = _make_result()
    out = tmp_path / "vpat.html"
    path = generate_vpat_report(result, out)
    assert path.exists()
    content = path.read_text()
    assert "VPAT" in content
    assert "A11yScope" in content
    assert "Perceivable" in content


def test_vpat_row_dataclass():
    row = VPATRow(
        criterion_id="1.1.1",
        criterion_name="Non-text Content",
        level="Supports",
        remarks="All images have alt text",
    )
    assert row.criterion_id == "1.1.1"
    assert row.level == "Supports"
