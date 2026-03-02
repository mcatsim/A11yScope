"""HTML report generation using Jinja2."""
from __future__ import annotations

from pathlib import Path
from datetime import datetime

from jinja2 import Environment, FileSystemLoader

from accessiflow.models import CourseAuditResult, Severity
from accessiflow.standards.mapping import CHECK_STANDARDS_MAP


def _score_class(score: float | None) -> str:
    if score is None:
        return "score-none"
    if score >= 90:
        return "score-pass"
    elif score >= 70:
        return "score-warn"
    return "score-fail"


def _severity_class(severity: Severity) -> str:
    return f"severity-{severity.value}"


def generate_html_report(result: CourseAuditResult, output_path: Path) -> Path:
    """Generate a standalone HTML report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Try package loader first, fall back to file system
    template_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=True,
    )
    env.filters["score_class"] = _score_class
    env.filters["severity_class"] = _severity_class

    template = env.get_template("report.html.j2")

    # Collect all issues with their parent item names
    all_issues = []
    for item in result.content_items:
        for issue in item.issues:
            mapping = CHECK_STANDARDS_MAP.get(issue.check_id)
            issue_dict = {"item_name": item.title, "item_type": item.content_type.value, **issue.model_dump()}
            if mapping:
                issue_dict["standards"] = {
                    "wcag_criteria": list(mapping.wcag_criteria),
                    "section_508": list(mapping.section_508_provisions),
                    "best_practice_urls": list(mapping.best_practice_urls),
                }
            all_issues.append(issue_dict)
    for item in result.file_items:
        for issue in item.issues:
            mapping = CHECK_STANDARDS_MAP.get(issue.check_id)
            issue_dict = {"item_name": item.display_name, "item_type": "file", **issue.model_dump()}
            if mapping:
                issue_dict["standards"] = {
                    "wcag_criteria": list(mapping.wcag_criteria),
                    "section_508": list(mapping.section_508_provisions),
                    "best_practice_urls": list(mapping.best_practice_urls),
                }
            all_issues.append(issue_dict)

    severity_order = {"critical": 0, "serious": 1, "moderate": 2, "minor": 3}
    all_issues.sort(key=lambda x: severity_order.get(x["severity"], 99))

    html = template.render(
        result=result,
        all_issues=all_issues,
        generated_at=datetime.now().isoformat(),
        score_class=_score_class,
        severity_class=_severity_class,
        CHECK_STANDARDS_MAP=CHECK_STANDARDS_MAP,
    )

    with open(output_path, "w") as f:
        f.write(html)

    return output_path
