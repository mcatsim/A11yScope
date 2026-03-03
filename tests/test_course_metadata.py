"""Tests for enhanced course metadata (Phase 2)."""
from __future__ import annotations

from datetime import datetime

import pytest

from a11yscope.models import CourseAuditResult


def test_course_audit_result_metadata_defaults():
    """CourseAuditResult should have empty/zero defaults for all metadata fields."""
    result = CourseAuditResult(
        course_id=1, course_name="Test", audit_timestamp=datetime.now()
    )
    assert result.course_code == ""
    assert result.term_name == ""
    assert result.instructor_name == ""
    assert result.instructor_email == ""
    assert result.enrollment_count == 0
    assert result.department == ""


def test_course_audit_result_with_metadata():
    """CourseAuditResult should accept and store all metadata fields."""
    result = CourseAuditResult(
        course_id=1,
        course_name="Test",
        audit_timestamp=datetime.now(),
        course_code="CS101",
        term_name="Fall 2025",
        instructor_name="Dr. Smith",
        instructor_email="smith@edu.com",
        enrollment_count=35,
        department="Computer Science",
    )
    assert result.course_code == "CS101"
    assert result.term_name == "Fall 2025"
    assert result.instructor_name == "Dr. Smith"
    assert result.instructor_email == "smith@edu.com"
    assert result.enrollment_count == 35
    assert result.department == "Computer Science"
