"""Weighted accessibility scoring engine."""
from canvas_a11y.models import (
    AccessibilityIssue, ContentItem, FileItem, CourseAuditResult, Severity,
)

# Severity weights
SEVERITY_WEIGHTS: dict[Severity, int] = {
    Severity.CRITICAL: 10,
    Severity.SERIOUS: 5,
    Severity.MODERATE: 3,
    Severity.MINOR: 1,
}

# Total possible checks per content item (the 14 HTML checks)
# Each check has a severity; for scoring, we compute based on what was actually checked
CHECKS_PER_CONTENT = 14
CHECKS_PER_FILE = 6  # varies by file type


def score_item(issues: list[AccessibilityIssue], total_checks: int = CHECKS_PER_CONTENT) -> float:
    """Calculate a 0-100 score for a single item based on issues found.

    Formula: score = (1 - failed_weight / total_weight) * 100

    Where total_weight is derived from the maximum possible weight
    (all checks at their severity levels), and failed_weight is the
    sum of weights of failed checks.
    """
    if total_checks == 0:
        return 100.0

    failed_weight = sum(SEVERITY_WEIGHTS.get(issue.severity, 1) for issue in issues if not issue.fixed)

    # Calculate total possible weight: assume a reasonable distribution
    # For simplicity, use the actual failed weight plus a baseline
    # Each check contributes at least 1 weight point
    total_weight = max(total_checks * 3, failed_weight + total_checks)  # baseline 3 per check

    if total_weight == 0:
        return 100.0

    score = (1 - failed_weight / total_weight) * 100
    return max(0.0, min(100.0, round(score, 1)))


def score_content_item(item: ContentItem) -> float:
    """Score a content item and set its score field."""
    if not item.html_content:
        item.score = 100.0
        return 100.0
    item.score = score_item(item.issues, CHECKS_PER_CONTENT)
    return item.score


def score_file_item(item: FileItem) -> float:
    """Score a file item and set its score field."""
    item.score = score_item(item.issues, CHECKS_PER_FILE)
    return item.score


def score_course(result: CourseAuditResult) -> float:
    """Calculate overall course score as average of all item scores."""
    scores = []
    for item in result.content_items:
        score_content_item(item)
        if item.score is not None:
            scores.append(item.score)
    for item in result.file_items:
        score_file_item(item)
        if item.score is not None:
            scores.append(item.score)

    if not scores:
        result.overall_score = 100.0
    else:
        result.overall_score = round(sum(scores) / len(scores), 1)

    return result.overall_score
