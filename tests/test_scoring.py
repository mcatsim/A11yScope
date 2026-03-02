"""Tests for the weighted accessibility scoring engine.

Covers:
- score_item: zero issues, single issue, multiple issues, severity ordering, fixed exclusion, bounds
- score_content_item / score_file_item: field mutation, empty content
- score_course: empty course, mixed items, overall score computation
- SEVERITY_WEIGHTS: expected weight values
"""
import pytest
from datetime import datetime

from canvas_a11y.scoring.engine import (
    score_item,
    score_content_item,
    score_file_item,
    score_course,
    SEVERITY_WEIGHTS,
    CHECKS_PER_CONTENT,
    CHECKS_PER_FILE,
)
from canvas_a11y.models import (
    AccessibilityIssue,
    ContentItem,
    FileItem,
    CourseAuditResult,
    Severity,
    ContentType,
)


def _make_issue(severity: Severity, fixed: bool = False) -> AccessibilityIssue:
    """Helper to create an issue with minimal required fields."""
    return AccessibilityIssue(
        check_id="test",
        title="Test",
        description="Test issue",
        severity=severity,
        wcag_criterion="1.1.1",
        fixed=fixed,
    )


# ---------------------------------------------------------------------------
# SEVERITY_WEIGHTS
# ---------------------------------------------------------------------------
class TestSeverityWeights:
    def test_critical_weight(self):
        assert SEVERITY_WEIGHTS[Severity.CRITICAL] == 10

    def test_serious_weight(self):
        assert SEVERITY_WEIGHTS[Severity.SERIOUS] == 5

    def test_moderate_weight(self):
        assert SEVERITY_WEIGHTS[Severity.MODERATE] == 3

    def test_minor_weight(self):
        assert SEVERITY_WEIGHTS[Severity.MINOR] == 1

    def test_ordering(self):
        """Weights should decrease with severity."""
        assert (
            SEVERITY_WEIGHTS[Severity.CRITICAL]
            > SEVERITY_WEIGHTS[Severity.SERIOUS]
            > SEVERITY_WEIGHTS[Severity.MODERATE]
            > SEVERITY_WEIGHTS[Severity.MINOR]
        )


# ---------------------------------------------------------------------------
# score_item
# ---------------------------------------------------------------------------
class TestScoreItem:
    def test_no_issues_perfect_score(self):
        score = score_item([], total_checks=14)
        assert score == 100.0

    def test_critical_issue_lowers_score(self):
        issues = [_make_issue(Severity.CRITICAL)]
        score = score_item(issues)
        assert score < 100.0

    def test_more_issues_lower_score(self):
        one = score_item([_make_issue(Severity.CRITICAL)])
        two = score_item([_make_issue(Severity.CRITICAL)] * 2)
        assert two < one

    def test_critical_worse_than_serious(self):
        critical = score_item([_make_issue(Severity.CRITICAL)])
        serious = score_item([_make_issue(Severity.SERIOUS)])
        assert critical < serious

    def test_critical_worse_than_moderate(self):
        critical = score_item([_make_issue(Severity.CRITICAL)])
        moderate = score_item([_make_issue(Severity.MODERATE)])
        assert critical < moderate

    def test_critical_worse_than_minor(self):
        critical = score_item([_make_issue(Severity.CRITICAL)])
        minor = score_item([_make_issue(Severity.MINOR)])
        assert critical < minor

    def test_serious_worse_than_minor(self):
        serious = score_item([_make_issue(Severity.SERIOUS)])
        minor = score_item([_make_issue(Severity.MINOR)])
        assert serious < minor

    def test_fixed_issues_not_counted(self):
        """Fixed issues should be excluded from the failed weight."""
        issue = _make_issue(Severity.CRITICAL, fixed=True)
        score = score_item([issue])
        assert score == 100.0

    def test_mixed_fixed_and_unfixed(self):
        """Only unfixed issues should reduce the score."""
        issues = [
            _make_issue(Severity.CRITICAL, fixed=True),
            _make_issue(Severity.MINOR, fixed=False),
        ]
        score = score_item(issues)
        # Should be lower than perfect but better than if the critical were unfixed
        assert score < 100.0
        assert score > score_item([_make_issue(Severity.CRITICAL), _make_issue(Severity.MINOR)])

    def test_score_bounded_lower(self):
        """Score should never go below 0 even with many critical issues."""
        issues = [_make_issue(Severity.CRITICAL) for _ in range(100)]
        score = score_item(issues)
        assert score >= 0.0

    def test_score_bounded_upper(self):
        """Score should never exceed 100."""
        score = score_item([])
        assert score <= 100.0

    def test_zero_total_checks(self):
        """Edge case: zero total checks should return 100."""
        score = score_item([], total_checks=0)
        assert score == 100.0


# ---------------------------------------------------------------------------
# score_content_item
# ---------------------------------------------------------------------------
class TestScoreContentItem:
    def test_scores_and_sets_field(self):
        item = ContentItem(
            id=1, content_type=ContentType.PAGE, title="P", url="",
            html_content="<p>Some content</p>",
        )
        item.issues = [_make_issue(Severity.SERIOUS)]
        result = score_content_item(item)
        assert item.score is not None
        assert item.score == result
        assert result < 100.0

    def test_no_html_content_returns_100(self):
        item = ContentItem(id=1, content_type=ContentType.PAGE, title="P", url="")
        result = score_content_item(item)
        assert result == 100.0
        assert item.score == 100.0

    def test_no_issues_returns_100(self):
        item = ContentItem(
            id=1, content_type=ContentType.PAGE, title="P", url="",
            html_content="<p>Clean</p>",
        )
        result = score_content_item(item)
        assert result == 100.0

    def test_uses_content_check_count(self):
        """score_content_item should use CHECKS_PER_CONTENT as total_checks."""
        item = ContentItem(
            id=1, content_type=ContentType.PAGE, title="P", url="",
            html_content="<p>Test</p>",
        )
        item.issues = [_make_issue(Severity.MINOR)]
        score_content_item(item)
        expected = score_item([_make_issue(Severity.MINOR)], CHECKS_PER_CONTENT)
        assert item.score == expected


# ---------------------------------------------------------------------------
# score_file_item
# ---------------------------------------------------------------------------
class TestScoreFileItem:
    def test_scores_and_sets_field(self):
        item = FileItem(
            id=1, display_name="Doc.pdf", filename="doc.pdf",
            content_type_header="application/pdf", size=1024, url="",
        )
        item.issues = [_make_issue(Severity.SERIOUS)]
        result = score_file_item(item)
        assert item.score is not None
        assert item.score == result
        assert result < 100.0

    def test_no_issues_returns_100(self):
        item = FileItem(
            id=1, display_name="Doc.pdf", filename="doc.pdf",
            content_type_header="application/pdf", size=1024, url="",
        )
        result = score_file_item(item)
        assert result == 100.0

    def test_uses_file_check_count(self):
        """score_file_item should use CHECKS_PER_FILE as total_checks."""
        item = FileItem(
            id=1, display_name="Doc.pdf", filename="doc.pdf",
            content_type_header="application/pdf", size=1024, url="",
        )
        item.issues = [_make_issue(Severity.MINOR)]
        score_file_item(item)
        expected = score_item([_make_issue(Severity.MINOR)], CHECKS_PER_FILE)
        assert item.score == expected


# ---------------------------------------------------------------------------
# score_course
# ---------------------------------------------------------------------------
class TestScoreCourse:
    def test_empty_course_returns_100(self):
        result = CourseAuditResult(
            course_id=1, course_name="Test", audit_timestamp=datetime.now(),
        )
        score = score_course(result)
        assert score == 100.0
        assert result.overall_score == 100.0

    def test_course_with_clean_content(self):
        result = CourseAuditResult(
            course_id=1, course_name="Test", audit_timestamp=datetime.now(),
            content_items=[
                ContentItem(
                    id=1, content_type=ContentType.PAGE, title="Page",
                    url="", html_content="<p>Clean content</p>",
                ),
            ],
        )
        score = score_course(result)
        assert score == 100.0

    def test_course_with_issues(self):
        item = ContentItem(
            id=1, content_type=ContentType.PAGE, title="Page",
            url="", html_content="<p>Test</p>",
        )
        item.issues = [_make_issue(Severity.CRITICAL)]
        result = CourseAuditResult(
            course_id=1, course_name="Test", audit_timestamp=datetime.now(),
            content_items=[item],
        )
        score = score_course(result)
        assert score < 100.0

    def test_course_score_is_average(self):
        """Overall score should be the average of all item scores."""
        clean_item = ContentItem(
            id=1, content_type=ContentType.PAGE, title="Clean",
            url="", html_content="<p>Clean</p>",
        )
        bad_item = ContentItem(
            id=2, content_type=ContentType.PAGE, title="Bad",
            url="", html_content="<p>Bad</p>",
        )
        bad_item.issues = [_make_issue(Severity.CRITICAL)]
        result = CourseAuditResult(
            course_id=1, course_name="Test", audit_timestamp=datetime.now(),
            content_items=[clean_item, bad_item],
        )
        score = score_course(result)
        # The average of 100 and the bad item's score
        bad_score = score_item([_make_issue(Severity.CRITICAL)], CHECKS_PER_CONTENT)
        expected = round((100.0 + bad_score) / 2, 1)
        assert score == expected

    def test_course_with_files(self):
        file_item = FileItem(
            id=1, display_name="Doc.pdf", filename="doc.pdf",
            content_type_header="application/pdf", size=1024, url="",
        )
        file_item.issues = [_make_issue(Severity.SERIOUS)]
        result = CourseAuditResult(
            course_id=1, course_name="Test", audit_timestamp=datetime.now(),
            file_items=[file_item],
        )
        score = score_course(result)
        assert score < 100.0
        assert result.overall_score == score

    def test_course_sets_overall_score_field(self):
        result = CourseAuditResult(
            course_id=1, course_name="Test", audit_timestamp=datetime.now(),
        )
        score_course(result)
        assert result.overall_score is not None

    def test_course_scores_all_items(self):
        """score_course should set the score field on every item."""
        item1 = ContentItem(
            id=1, content_type=ContentType.PAGE, title="P1",
            url="", html_content="<p>A</p>",
        )
        item2 = ContentItem(
            id=2, content_type=ContentType.PAGE, title="P2",
            url="", html_content="<p>B</p>",
        )
        result = CourseAuditResult(
            course_id=1, course_name="Test", audit_timestamp=datetime.now(),
            content_items=[item1, item2],
        )
        score_course(result)
        assert item1.score is not None
        assert item2.score is not None
