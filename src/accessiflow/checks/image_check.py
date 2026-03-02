"""Image file accessibility check."""
from pathlib import Path

from accessiflow.models import AccessibilityIssue, Severity
from accessiflow.checks.base import AccessibilityCheck
from accessiflow.checks.registry import register_check


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".svg", ".bmp", ".webp", ".tiff", ".tif"}


@register_check
class ImageFileMissingContext(AccessibilityCheck):
    check_id = "image-file-no-context"
    title = "Image files without contextual alt text"
    description = "Standalone image files uploaded to Canvas lack alt text unless set in Canvas file properties"
    wcag_criterion = "1.1.1"

    def check_html(self, html: str, url: str = "") -> list[AccessibilityIssue]:
        return []

    def check_file(self, file_path: Path) -> list[AccessibilityIssue]:
        if file_path.suffix.lower() not in IMAGE_EXTENSIONS:
            return []
        # Standalone image files in Canvas Files don't have alt text context
        # They only get alt text when embedded in HTML content
        return [self._make_issue(
            f"Image file '{file_path.name}' may lack alt text when embedded in content",
            severity=Severity.SERIOUS,
            ai_fixable=True,
        )]
