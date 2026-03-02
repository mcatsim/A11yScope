"""VPAT HTML report generator."""
from __future__ import annotations

from pathlib import Path
from datetime import datetime

from jinja2 import Environment, FileSystemLoader

from accessiflow.models import CourseAuditResult
from accessiflow.standards.vpat import build_vpat, VPATReport
from accessiflow.standards.wcag21 import WCAG_CRITERIA


def generate_vpat_report(result: CourseAuditResult, output_path: Path) -> Path:
    """Generate a VPAT 2.x WCAG Edition HTML report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    vpat = build_vpat(result)

    template_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=True,
    )

    template = env.get_template("vpat_report.html.j2")

    # Group rows by principle
    principles = ["Perceivable", "Operable", "Understandable", "Robust"]
    grouped_rows = {}
    for principle in principles:
        grouped_rows[principle] = [
            row for row in vpat.rows
            if WCAG_CRITERIA.get(row.criterion_id, None) and
               WCAG_CRITERIA[row.criterion_id].principle == principle
        ]

    html = template.render(
        vpat=vpat,
        grouped_rows=grouped_rows,
        principles=principles,
        wcag_criteria=WCAG_CRITERIA,
        generated_at=datetime.now().isoformat(),
    )

    with open(output_path, "w") as f:
        f.write(html)

    return output_path
