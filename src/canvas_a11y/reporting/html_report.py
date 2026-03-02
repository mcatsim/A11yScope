"""HTML report generation using Jinja2."""
from pathlib import Path
from datetime import datetime

from jinja2 import Environment, FileSystemLoader

from canvas_a11y.models import CourseAuditResult, Severity


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
            all_issues.append({"item_name": item.title, "item_type": item.content_type.value, **issue.model_dump()})
    for item in result.file_items:
        for issue in item.issues:
            all_issues.append({"item_name": item.display_name, "item_type": "file", **issue.model_dump()})

    severity_order = {"critical": 0, "serious": 1, "moderate": 2, "minor": 3}
    all_issues.sort(key=lambda x: severity_order.get(x["severity"], 99))

    html = template.render(
        result=result,
        all_issues=all_issues,
        generated_at=datetime.now().isoformat(),
        score_class=_score_class,
        severity_class=_severity_class,
    )

    with open(output_path, "w") as f:
        f.write(html)

    return output_path
