"""Tests for Pydantic data models.

Covers:
- Severity and ContentType StrEnum values
- AccessibilityIssue defaults and field validation
- ContentItem construction and issue accumulation
- FileItem construction
- CourseAuditResult computed fields: total_issues, severity counts, pass/fail counts
"""
import pytest
from datetime import datetime
from pathlib import Path

from accessiflow.models import (
    AccessibilityIssue,
    ContentItem,
    FileItem,
    CourseAuditResult,
    Severity,
    ContentType,
)


# ---------------------------------------------------------------------------
# Severity enum
# ---------------------------------------------------------------------------
class TestSeverity:
    def test_values(self):
        assert Severity.CRITICAL == "critical"
        assert Severity.SERIOUS == "serious"
        assert Severity.MODERATE == "moderate"
        assert Severity.MINOR == "minor"

    def test_is_strenum(self):
        assert isinstance(Severity.CRITICAL, str)

    def test_all_members(self):
        members = list(Severity)
        assert len(members) == 4


# ---------------------------------------------------------------------------
# ContentType enum
# ---------------------------------------------------------------------------
class TestContentType:
    def test_values(self):
        assert ContentType.PAGE == "page"
        assert ContentType.ASSIGNMENT == "assignment"
        assert ContentType.DISCUSSION == "discussion"
        assert ContentType.QUIZ == "quiz"
        assert ContentType.FILE == "file"
        assert ContentType.SYLLABUS == "syllabus"
        assert ContentType.ANNOUNCEMENT == "announcement"

    def test_all_members(self):
        members = list(ContentType)
        assert len(members) == 7


# ---------------------------------------------------------------------------
# AccessibilityIssue
# ---------------------------------------------------------------------------
class TestAccessibilityIssue:
    def test_required_fields(self):
        issue = AccessibilityIssue(
            check_id="alt-text-missing",
            title="Missing alt",
            description="Image missing alt attribute",
            severity=Severity.CRITICAL,
            wcag_criterion="1.1.1",
        )
        assert issue.check_id == "alt-text-missing"
        assert issue.severity == Severity.CRITICAL

    def test_defaults(self):
        issue = AccessibilityIssue(
            check_id="test", title="T", description="D",
            severity=Severity.MINOR, wcag_criterion="1.1.1",
        )
        assert issue.element_html is None
        assert issue.line_number is None
        assert issue.auto_fixable is False
        assert issue.ai_fixable is False
        assert issue.fixed is False
        assert issue.fix_description is None

    def test_optional_fields(self):
        issue = AccessibilityIssue(
            check_id="test", title="T", description="D",
            severity=Severity.SERIOUS, wcag_criterion="1.3.1",
            element_html='<img src="x.jpg">', line_number=42,
            auto_fixable=True, ai_fixable=True,
            fixed=True, fix_description="Added alt text",
        )
        assert issue.element_html == '<img src="x.jpg">'
        assert issue.line_number == 42
        assert issue.auto_fixable is True
        assert issue.ai_fixable is True
        assert issue.fixed is True
        assert issue.fix_description == "Added alt text"

    def test_serialization_roundtrip(self):
        issue = AccessibilityIssue(
            check_id="test", title="T", description="D",
            severity=Severity.CRITICAL, wcag_criterion="1.1.1",
        )
        data = issue.model_dump()
        restored = AccessibilityIssue(**data)
        assert restored == issue


# ---------------------------------------------------------------------------
# ContentItem
# ---------------------------------------------------------------------------
class TestContentItem:
    def test_construction(self):
        item = ContentItem(
            id=1, content_type=ContentType.PAGE, title="Syllabus",
            url="https://canvas.example.com/courses/1/pages/syllabus",
        )
        assert item.id == 1
        assert item.content_type == ContentType.PAGE
        assert item.html_content is None
        assert item.issues == []
        assert item.score is None

    def test_with_html_and_issues(self):
        issue = AccessibilityIssue(
            check_id="test", title="T", description="D",
            severity=Severity.MINOR, wcag_criterion="1.1.1",
        )
        item = ContentItem(
            id=1, content_type=ContentType.ASSIGNMENT, title="HW1",
            url="", html_content="<p>Hello</p>", issues=[issue], score=95.0,
        )
        assert len(item.issues) == 1
        assert item.score == 95.0

    def test_issues_mutable(self):
        item = ContentItem(
            id=1, content_type=ContentType.PAGE, title="P", url="",
        )
        issue = AccessibilityIssue(
            check_id="a", title="A", description="A",
            severity=Severity.CRITICAL, wcag_criterion="1.1.1",
        )
        item.issues.append(issue)
        assert len(item.issues) == 1


# ---------------------------------------------------------------------------
# FileItem
# ---------------------------------------------------------------------------
class TestFileItem:
    def test_construction(self):
        item = FileItem(
            id=100, display_name="Syllabus.pdf", filename="syllabus.pdf",
            content_type_header="application/pdf", size=102400,
            url="https://canvas.example.com/files/100/download",
        )
        assert item.id == 100
        assert item.display_name == "Syllabus.pdf"
        assert item.issues == []
        assert item.score is None
        assert item.local_path is None
        assert item.remediated_path is None

    def test_with_paths(self):
        item = FileItem(
            id=100, display_name="Doc.pdf", filename="doc.pdf",
            content_type_header="application/pdf", size=1024,
            url="", local_path=Path("/tmp/doc.pdf"),
            remediated_path=Path("/tmp/doc_fixed.pdf"),
        )
        assert item.local_path == Path("/tmp/doc.pdf")
        assert item.remediated_path == Path("/tmp/doc_fixed.pdf")


# ---------------------------------------------------------------------------
# CourseAuditResult — computed fields
# ---------------------------------------------------------------------------
class TestCourseAuditResult:
    def _make_issue(self, severity: Severity) -> AccessibilityIssue:
        return AccessibilityIssue(
            check_id="test", title="T", description="D",
            severity=severity, wcag_criterion="1.1.1",
        )

    def test_total_issues_from_content(self):
        item = ContentItem(id=1, content_type=ContentType.PAGE, title="P", url="")
        item.issues = [self._make_issue(Severity.CRITICAL), self._make_issue(Severity.MINOR)]
        result = CourseAuditResult(
            course_id=1, course_name="Test", audit_timestamp=datetime.now(),
            content_items=[item],
        )
        assert result.total_issues == 2

    def test_total_issues_from_files(self):
        file_item = FileItem(
            id=1, display_name="F.pdf", filename="f.pdf",
            content_type_header="application/pdf", size=100, url="",
        )
        file_item.issues = [self._make_issue(Severity.SERIOUS)]
        result = CourseAuditResult(
            course_id=1, course_name="Test", audit_timestamp=datetime.now(),
            file_items=[file_item],
        )
        assert result.total_issues == 1

    def test_total_issues_combined(self):
        content = ContentItem(id=1, content_type=ContentType.PAGE, title="P", url="")
        content.issues = [self._make_issue(Severity.CRITICAL)]
        file_item = FileItem(
            id=1, display_name="F.pdf", filename="f.pdf",
            content_type_header="application/pdf", size=100, url="",
        )
        file_item.issues = [self._make_issue(Severity.MINOR), self._make_issue(Severity.MINOR)]
        result = CourseAuditResult(
            course_id=1, course_name="Test", audit_timestamp=datetime.now(),
            content_items=[content], file_items=[file_item],
        )
        assert result.total_issues == 3

    def test_severity_counts(self):
        item = ContentItem(id=1, content_type=ContentType.PAGE, title="P", url="")
        item.issues = [
            self._make_issue(Severity.CRITICAL),
            self._make_issue(Severity.CRITICAL),
            self._make_issue(Severity.SERIOUS),
            self._make_issue(Severity.MODERATE),
            self._make_issue(Severity.MINOR),
        ]
        result = CourseAuditResult(
            course_id=1, course_name="Test", audit_timestamp=datetime.now(),
            content_items=[item],
        )
        assert result.critical_count == 2
        assert result.serious_count == 1
        assert result.moderate_count == 1
        assert result.minor_count == 1

    def test_severity_counts_zero(self):
        result = CourseAuditResult(
            course_id=1, course_name="Test", audit_timestamp=datetime.now(),
        )
        assert result.critical_count == 0
        assert result.serious_count == 0
        assert result.moderate_count == 0
        assert result.minor_count == 0

    def test_items_passing(self):
        passing = ContentItem(id=1, content_type=ContentType.PAGE, title="P", url="")
        passing.score = 95.0
        borderline = ContentItem(id=2, content_type=ContentType.PAGE, title="Q", url="")
        borderline.score = 90.0  # Exactly 90 should pass
        result = CourseAuditResult(
            course_id=1, course_name="Test", audit_timestamp=datetime.now(),
            content_items=[passing, borderline],
        )
        assert result.items_passing == 2

    def test_items_failing(self):
        failing = ContentItem(id=1, content_type=ContentType.PAGE, title="P", url="")
        failing.score = 50.0
        barely_failing = ContentItem(id=2, content_type=ContentType.PAGE, title="Q", url="")
        barely_failing.score = 89.9
        result = CourseAuditResult(
            course_id=1, course_name="Test", audit_timestamp=datetime.now(),
            content_items=[failing, barely_failing],
        )
        assert result.items_failing == 2

    def test_items_passing_and_failing(self):
        passing = ContentItem(id=1, content_type=ContentType.PAGE, title="P", url="")
        passing.score = 95.0
        failing = ContentItem(id=2, content_type=ContentType.PAGE, title="Q", url="")
        failing.score = 50.0
        result = CourseAuditResult(
            course_id=1, course_name="Test", audit_timestamp=datetime.now(),
            content_items=[passing, failing],
        )
        assert result.items_passing == 1
        assert result.items_failing == 1

    def test_unscored_items_excluded(self):
        """Items without a score (None) should not count as passing or failing."""
        unscored = ContentItem(id=1, content_type=ContentType.PAGE, title="P", url="")
        assert unscored.score is None
        result = CourseAuditResult(
            course_id=1, course_name="Test", audit_timestamp=datetime.now(),
            content_items=[unscored],
        )
        assert result.items_passing == 0
        assert result.items_failing == 0

    def test_file_items_in_pass_fail(self):
        """FileItems should also be included in passing/failing counts."""
        passing_file = FileItem(
            id=1, display_name="F.pdf", filename="f.pdf",
            content_type_header="application/pdf", size=100, url="",
        )
        passing_file.score = 100.0
        failing_file = FileItem(
            id=2, display_name="G.pdf", filename="g.pdf",
            content_type_header="application/pdf", size=200, url="",
        )
        failing_file.score = 40.0
        result = CourseAuditResult(
            course_id=1, course_name="Test", audit_timestamp=datetime.now(),
            file_items=[passing_file, failing_file],
        )
        assert result.items_passing == 1
        assert result.items_failing == 1

    def test_empty_result(self):
        result = CourseAuditResult(
            course_id=1, course_name="Test", audit_timestamp=datetime.now(),
        )
        assert result.total_issues == 0
        assert result.critical_count == 0
        assert result.serious_count == 0
        assert result.moderate_count == 0
        assert result.minor_count == 0
        assert result.items_passing == 0
        assert result.items_failing == 0

    def test_serialization_includes_computed_fields(self):
        item = ContentItem(id=1, content_type=ContentType.PAGE, title="P", url="")
        item.issues = [self._make_issue(Severity.CRITICAL)]
        item.score = 70.0
        result = CourseAuditResult(
            course_id=1, course_name="Test", audit_timestamp=datetime.now(),
            content_items=[item],
        )
        data = result.model_dump()
        assert "total_issues" in data
        assert data["total_issues"] == 1
        assert "critical_count" in data
        assert data["critical_count"] == 1
        assert "items_failing" in data
        assert data["items_failing"] == 1
