"""Pydantic data models for Canvas LMS accessibility audit results."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    from enum import Enum

    class StrEnum(str, Enum):
        """Backport of StrEnum for Python < 3.11."""
        pass

from pydantic import BaseModel, computed_field


class Severity(StrEnum):
    """WCAG violation severity levels."""

    CRITICAL = "critical"
    SERIOUS = "serious"
    MODERATE = "moderate"
    MINOR = "minor"


class ContentType(StrEnum):
    """Types of Canvas LMS content that can be audited."""

    PAGE = "page"
    ASSIGNMENT = "assignment"
    DISCUSSION = "discussion"
    ANNOUNCEMENT = "announcement"
    SYLLABUS = "syllabus"
    QUIZ = "quiz"
    FILE = "file"


class AccessibilityIssue(BaseModel):
    """A single accessibility issue found during an audit check."""

    check_id: str
    """Machine-readable identifier, e.g. 'alt-text-missing'."""

    title: str
    """Human-readable short title of the issue."""

    description: str
    """Detailed explanation of why this is an accessibility barrier."""

    severity: Severity
    """WCAG violation severity level."""

    wcag_criterion: str
    """WCAG success criterion reference, e.g. '1.1.1'."""

    element_html: Optional[str] = None
    """Snippet of the offending HTML element, if applicable."""

    line_number: Optional[int] = None
    """Approximate line number in the source HTML where the issue occurs."""

    auto_fixable: bool = False
    """Whether this issue can be fixed automatically via deterministic rules."""

    ai_fixable: bool = False
    """Whether this issue can be fixed with AI-assisted remediation."""

    fixed: bool = False
    """Whether this issue has been remediated."""

    fix_description: Optional[str] = None
    """Description of the fix that was applied, if any."""


class ContentItem(BaseModel):
    """A piece of HTML content from Canvas (page, assignment, discussion, etc.)."""

    id: int
    """Canvas object ID."""

    content_type: ContentType
    """The type of Canvas content this item represents."""

    title: str
    """Display title of the content item."""

    url: str
    """Canvas URL for the content item."""

    html_content: Optional[str] = None
    """Raw HTML body of the content, fetched from the Canvas API."""

    issues: List[AccessibilityIssue] = []
    """Accessibility issues found in this content item."""

    score: Optional[float] = None
    """Accessibility score from 0-100; None if not yet scored."""


class FileItem(BaseModel):
    """A file uploaded to Canvas (PDF, DOCX, image, etc.)."""

    id: int
    """Canvas file ID."""

    display_name: str
    """User-facing display name of the file."""

    filename: str
    """Original filename on disk."""

    content_type_header: str
    """MIME type of the file, e.g. 'application/pdf'."""

    size: int
    """File size in bytes."""

    url: str
    """Canvas download URL for the file."""

    issues: List[AccessibilityIssue] = []
    """Accessibility issues found in this file."""

    score: Optional[float] = None
    """Accessibility score from 0-100; None if not yet scored."""

    local_path: Optional[Path] = None
    """Path to the locally downloaded copy of the file."""

    remediated_path: Optional[Path] = None
    """Path to the remediated version of the file, if generated."""


class CourseAuditResult(BaseModel):
    """Aggregate audit result for an entire Canvas course."""

    course_id: int
    """Canvas course ID."""

    course_name: str
    """Human-readable course name."""

    audit_timestamp: datetime
    """When the audit was performed."""

    content_items: List[ContentItem] = []
    """All HTML content items audited in this course."""

    file_items: List[FileItem] = []
    """All files audited in this course."""

    overall_score: Optional[float] = None
    """Weighted overall accessibility score from 0-100; None if not yet computed."""

    # Course metadata (populated during audit)
    course_code: str = ""
    """Canvas course code, e.g. 'CS101-F25'."""

    term_name: str = ""
    """Academic term name, e.g. 'Fall 2025'."""

    instructor_name: str = ""
    """Primary instructor display name."""

    instructor_email: str = ""
    """Primary instructor email address."""

    enrollment_count: int = 0
    """Total number of enrolled students."""

    department: str = ""
    """Department or account name from Canvas."""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_issues(self) -> int:
        """Total number of accessibility issues found across all items."""
        content_issues = sum(len(item.issues) for item in self.content_items)
        file_issues = sum(len(item.issues) for item in self.file_items)
        return content_issues + file_issues

    @computed_field  # type: ignore[prop-decorator]
    @property
    def critical_count(self) -> int:
        """Number of critical-severity issues."""
        return self._count_by_severity(Severity.CRITICAL)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def serious_count(self) -> int:
        """Number of serious-severity issues."""
        return self._count_by_severity(Severity.SERIOUS)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def moderate_count(self) -> int:
        """Number of moderate-severity issues."""
        return self._count_by_severity(Severity.MODERATE)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def minor_count(self) -> int:
        """Number of minor-severity issues."""
        return self._count_by_severity(Severity.MINOR)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def items_passing(self) -> int:
        """Number of items with an accessibility score >= 90."""
        return self._count_by_score_threshold(passing=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def items_failing(self) -> int:
        """Number of items with an accessibility score < 90."""
        return self._count_by_score_threshold(passing=False)

    def _count_by_severity(self, severity: Severity) -> int:
        """Count issues matching a given severity across all items."""
        count = 0
        for item in self.content_items:
            count += sum(1 for issue in item.issues if issue.severity == severity)
        for item in self.file_items:
            count += sum(1 for issue in item.issues if issue.severity == severity)
        return count

    def _count_by_score_threshold(self, *, passing: bool) -> int:
        """Count scored items that are passing (>= 90) or failing (< 90).

        Items without a score (None) are excluded from both counts.
        """
        all_items: List[Union[ContentItem, FileItem]] = [
            *self.content_items,
            *self.file_items,
        ]
        count = 0
        for item in all_items:
            if item.score is not None:
                if passing and item.score >= 90:
                    count += 1
                elif not passing and item.score < 90:
                    count += 1
        return count
