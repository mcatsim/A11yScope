"""Shared test fixtures for Canvas LMS Accessibility Auditor tests."""
import pytest
from datetime import datetime

from canvas_a11y.models import (
    AccessibilityIssue,
    ContentItem,
    FileItem,
    CourseAuditResult,
    Severity,
    ContentType,
)


@pytest.fixture
def sample_html_clean():
    """Well-formed HTML that should pass all accessibility checks."""
    return (
        '<h1>Title</h1>'
        '<p>Some text with <a href="/link">descriptive link text</a></p>'
        '<img src="test.jpg" alt="A student studying at a desk">'
        '<table><caption>Grade summary</caption>'
        '<thead><tr><th scope="col">Name</th><th scope="col">Grade</th></tr></thead>'
        '<tbody><tr><td>Alice</td><td>95</td></tr></tbody></table>'
        '<label for="search">Search</label><input type="text" id="search">'
        '<button>Submit</button>'
        '<iframe src="https://example.com" title="Embedded content"></iframe>'
        '<video src="lecture.mp4"><track kind="captions" src="caps.vtt"></video>'
    )


@pytest.fixture
def sample_html_bad():
    """HTML that triggers every accessibility check with at least one issue."""
    return '''
    <h1>Title</h1>
    <h3>Skipped h2</h3>
    <img src="photo.jpg">
    <img src="logo.png" alt="image1.jpg">
    <a href="/page">click here</a>
    <a href="/empty"></a>
    <table><tr><td>No headers</td></tr></table>
    <table><tr><th>Name</th><th>Value</th></tr><tr><td>A</td><td>1</td></tr></table>
    <iframe src="https://example.com"></iframe>
    <button></button>
    <video src="video.mp4"></video>
    <input type="text" id="name">
    <font color="red">Old element</font>
    <center>Centered</center>
    <span style="color: #777777; background-color: #ffffff">Low contrast</span>
    '''


@pytest.fixture
def sample_content_item(sample_html_bad):
    """A ContentItem populated with bad HTML for testing."""
    return ContentItem(
        id=1,
        content_type=ContentType.PAGE,
        title="Test Page",
        url="https://canvas.example.com/courses/1/pages/test",
        html_content=sample_html_bad,
    )


@pytest.fixture
def sample_issue():
    """A single critical accessibility issue."""
    return AccessibilityIssue(
        check_id="alt-text-missing",
        title="Image missing alt text",
        description="Image missing alt attribute",
        severity=Severity.CRITICAL,
        wcag_criterion="1.1.1",
    )


@pytest.fixture
def sample_file_item():
    """A FileItem for testing file-related scoring."""
    return FileItem(
        id=100,
        display_name="Syllabus.pdf",
        filename="syllabus.pdf",
        content_type_header="application/pdf",
        size=102400,
        url="https://canvas.example.com/files/100/download",
    )


@pytest.fixture
def sample_course_result():
    """An empty CourseAuditResult for testing."""
    return CourseAuditResult(
        course_id=12345,
        course_name="Test Course",
        audit_timestamp=datetime(2026, 3, 2, 12, 0, 0),
    )


@pytest.fixture
def make_issue():
    """Factory fixture for creating AccessibilityIssue instances with defaults."""
    def _make(
        check_id: str = "test-check",
        severity: Severity = Severity.SERIOUS,
        auto_fixable: bool = False,
        fixed: bool = False,
    ) -> AccessibilityIssue:
        return AccessibilityIssue(
            check_id=check_id,
            title=f"Test issue ({check_id})",
            description=f"Description for {check_id}",
            severity=severity,
            wcag_criterion="1.1.1",
            auto_fixable=auto_fixable,
            fixed=fixed,
        )
    return _make
