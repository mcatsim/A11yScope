"""JSON report export."""
import json
from pathlib import Path
from datetime import datetime

from a11yscope.models import CourseAuditResult


def generate_json_report(result: CourseAuditResult, output_path: Path) -> Path:
    """Generate a machine-readable JSON report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = result.model_dump(mode="json")
    data["generated_at"] = datetime.now().isoformat()

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, default=str)

    return output_path
