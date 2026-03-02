"""VPAT (Voluntary Product Accessibility Template) report builder.

Generates a structured VPAT report from a ``CourseAuditResult`` by mapping
each discovered issue back to the WCAG 2.1 success criteria it violates and
determining conformance levels per criterion.

The output conforms to the ITI VPAT 2.4 Rev Section 508 Edition format.
Reference: https://www.itic.org/policy/accessibility/vpat
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from accessiflow.models import (
    AccessibilityIssue,
    CourseAuditResult,
    Severity,
)
from accessiflow.standards.mapping import CHECK_STANDARDS_MAP
from accessiflow.standards.wcag21 import WCAG_CRITERIA, WCAGCriterion


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

class ConformanceLevel:
    """VPAT conformance level constants."""

    SUPPORTS = "Supports"
    PARTIALLY_SUPPORTS = "Partially Supports"
    DOES_NOT_SUPPORT = "Does Not Support"
    NOT_EVALUATED = "Not Evaluated"
    NOT_APPLICABLE = "Not Applicable"


@dataclass
class VPATRow:
    """A single row in the VPAT conformance table."""

    criterion_id: str
    """WCAG success criterion ID, e.g. '1.1.1'."""

    criterion_name: str
    """Human-readable criterion name, e.g. 'Non-text Content'."""

    level: str
    """Conformance level: one of the ConformanceLevel constants."""

    remarks: str = ""
    """Explanation of the conformance finding."""


@dataclass
class VPATReport:
    """A complete VPAT report for a product / course."""

    product_name: str
    """Name of the product or course being evaluated."""

    report_date: str
    """ISO-format date when the report was generated."""

    rows: list[VPATRow] = field(default_factory=list)
    """Conformance rows, one per WCAG criterion."""

    notes: str = ""
    """Additional notes about evaluation scope or methodology."""

    @property
    def supports_count(self) -> int:
        """Number of criteria that fully support conformance."""
        return sum(1 for r in self.rows if r.level == ConformanceLevel.SUPPORTS)

    @property
    def partially_supports_count(self) -> int:
        """Number of criteria that partially support conformance."""
        return sum(1 for r in self.rows if r.level == ConformanceLevel.PARTIALLY_SUPPORTS)

    @property
    def does_not_support_count(self) -> int:
        """Number of criteria that do not support conformance."""
        return sum(1 for r in self.rows if r.level == ConformanceLevel.DOES_NOT_SUPPORT)

    @property
    def not_evaluated_count(self) -> int:
        """Number of criteria that were not evaluated."""
        return sum(1 for r in self.rows if r.level == ConformanceLevel.NOT_EVALUATED)

    @property
    def conformance_percentage(self) -> float:
        """Percentage of evaluated criteria that fully or partially support."""
        evaluated = [
            r for r in self.rows
            if r.level not in (ConformanceLevel.NOT_EVALUATED, ConformanceLevel.NOT_APPLICABLE)
        ]
        if not evaluated:
            return 0.0
        passing = sum(
            1 for r in evaluated
            if r.level in (ConformanceLevel.SUPPORTS, ConformanceLevel.PARTIALLY_SUPPORTS)
        )
        return round((passing / len(evaluated)) * 100, 1)


# ---------------------------------------------------------------------------
# Severity classification helpers
# ---------------------------------------------------------------------------

_HIGH_SEVERITY = frozenset({Severity.CRITICAL, Severity.SERIOUS})
_LOW_SEVERITY = frozenset({Severity.MODERATE, Severity.MINOR})


def _classify_issues(issues: list[AccessibilityIssue]) -> str:
    """Determine conformance level from a list of issues for one criterion.

    Rules:
    - No unfixed issues -> Supports
    - Only minor/moderate unfixed issues -> Partially Supports
    - Any critical/serious unfixed issues -> Does Not Support
    """
    unfixed = [i for i in issues if not i.fixed]
    if not unfixed:
        return ConformanceLevel.SUPPORTS

    severities = {i.severity for i in unfixed}
    if severities & _HIGH_SEVERITY:
        return ConformanceLevel.DOES_NOT_SUPPORT
    return ConformanceLevel.PARTIALLY_SUPPORTS


def _build_remarks(issues: list[AccessibilityIssue], level: str) -> str:
    """Build a human-readable remarks string for a VPAT row."""
    unfixed = [i for i in issues if not i.fixed]

    if level == ConformanceLevel.SUPPORTS:
        if issues:
            return "All identified issues have been remediated."
        return "No issues identified during automated testing."

    if level == ConformanceLevel.NOT_EVALUATED:
        return "This criterion is not covered by the current set of automated checks."

    # Summarize unfixed issues by check_id
    check_counts: dict[str, int] = {}
    for issue in unfixed:
        check_counts[issue.check_id] = check_counts.get(issue.check_id, 0) + 1

    parts = [f"{count} {check_id} issue(s)" for check_id, count in sorted(check_counts.items())]
    summary = "; ".join(parts)

    if level == ConformanceLevel.DOES_NOT_SUPPORT:
        return f"Critical/serious issues found: {summary}."
    # Partially Supports
    return f"Minor/moderate issues found: {summary}."


# ---------------------------------------------------------------------------
# VPAT builder
# ---------------------------------------------------------------------------

def _collect_all_issues(result: CourseAuditResult) -> list[AccessibilityIssue]:
    """Collect every issue from all content items and file items."""
    issues: list[AccessibilityIssue] = []
    for item in result.content_items:
        issues.extend(item.issues)
    for item in result.file_items:
        issues.extend(item.issues)
    return issues


def _build_criterion_issue_map(
    all_issues: list[AccessibilityIssue],
) -> dict[str, list[AccessibilityIssue]]:
    """Map each WCAG criterion ID to the issues that violate it.

    Uses two sources:
    1. The ``wcag_criterion`` field on each ``AccessibilityIssue``
    2. The ``CHECK_STANDARDS_MAP`` to find additional criteria a check covers
    """
    criterion_issues: dict[str, list[AccessibilityIssue]] = {}

    for issue in all_issues:
        # Direct criterion reference from the issue
        if issue.wcag_criterion:
            criterion_issues.setdefault(issue.wcag_criterion, []).append(issue)

        # Additional criteria from the standards mapping
        mapping = CHECK_STANDARDS_MAP.get(issue.check_id)
        if mapping:
            for cid in mapping.wcag_criteria:
                if cid != issue.wcag_criterion:
                    criterion_issues.setdefault(cid, []).append(issue)

    return criterion_issues


def _get_covered_criteria() -> set[str]:
    """Return the set of WCAG criterion IDs covered by at least one check."""
    covered: set[str] = set()
    for mapping in CHECK_STANDARDS_MAP.values():
        covered.update(mapping.wcag_criteria)
    return covered


def build_vpat(result: CourseAuditResult) -> VPATReport:
    """Build a VPAT from a CourseAuditResult.

    For each WCAG criterion in ``WCAG_CRITERIA``:
    - Find all issues that map to this criterion (via ``CHECK_STANDARDS_MAP``
      and the issue's ``wcag_criterion`` field).
    - No issues found and criterion is covered by our checks -> ``Supports``
    - Only minor/moderate unfixed issues -> ``Partially Supports``
    - Any critical/serious unfixed issues -> ``Does Not Support``
    - Criterion not covered by any of our checks -> ``Not Evaluated``

    Args:
        result: A completed course audit result with scored content and file items.

    Returns:
        A ``VPATReport`` with rows ordered by principle (Perceivable, Operable,
        Understandable, Robust) and then by criterion ID.
    """
    all_issues = _collect_all_issues(result)
    criterion_issue_map = _build_criterion_issue_map(all_issues)
    covered_criteria = _get_covered_criteria()

    rows: list[VPATRow] = []

    # Process criteria in principle order, then by ID
    principle_order = ("Perceivable", "Operable", "Understandable", "Robust")
    sorted_criteria = sorted(
        WCAG_CRITERIA.values(),
        key=lambda c: (
            principle_order.index(c.principle),
            [int(x) for x in c.id.split(".")],
        ),
    )

    for criterion in sorted_criteria:
        issues_for_criterion = criterion_issue_map.get(criterion.id, [])

        if criterion.id not in covered_criteria:
            # We have no checks that evaluate this criterion
            level = ConformanceLevel.NOT_EVALUATED
        else:
            level = _classify_issues(issues_for_criterion)

        remarks = _build_remarks(issues_for_criterion, level)

        rows.append(VPATRow(
            criterion_id=criterion.id,
            criterion_name=criterion.name,
            level=level,
            remarks=remarks,
        ))

    return VPATReport(
        product_name=result.course_name,
        report_date=datetime.now().strftime("%Y-%m-%d"),
        rows=rows,
        notes=(
            f"Automated accessibility audit of Canvas course "
            f"'{result.course_name}' (ID: {result.course_id}). "
            f"This report covers {len(covered_criteria)} of "
            f"{len(WCAG_CRITERIA)} WCAG 2.1 Level A and AA criteria "
            f"via {len(CHECK_STANDARDS_MAP)} automated checks. "
            f"Criteria marked 'Not Evaluated' require manual testing."
        ),
    )
