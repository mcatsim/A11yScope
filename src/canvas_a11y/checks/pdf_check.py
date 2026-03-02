"""PDF accessibility checks."""
from pathlib import Path

from canvas_a11y.models import AccessibilityIssue, Severity
from canvas_a11y.checks.base import AccessibilityCheck
from canvas_a11y.checks.registry import register_check


@register_check
class PDFNotTagged(AccessibilityCheck):
    check_id = "pdf-not-tagged"
    title = "PDF not tagged"
    description = "PDFs must have a tagged structure (StructTreeRoot) for screen readers"
    wcag_criterion = "1.3.1"

    def check_html(self, html: str, url: str = "") -> list[AccessibilityIssue]:
        return []

    def check_file(self, file_path: Path) -> list[AccessibilityIssue]:
        if not file_path.suffix.lower() == ".pdf":
            return []
        try:
            import pikepdf
            with pikepdf.open(file_path) as pdf:
                catalog = pdf.Root
                has_struct = "/StructTreeRoot" in catalog
                has_mark_info = "/MarkInfo" in catalog
                if has_mark_info:
                    marked = catalog["/MarkInfo"].get("/Marked", False)
                    if hasattr(marked, '__bool__'):
                        has_mark_info = bool(marked)

                if not has_struct and not has_mark_info:
                    return [self._make_issue(
                        f"PDF is not tagged (no StructTreeRoot or MarkInfo): {file_path.name}",
                        severity=Severity.CRITICAL,
                    )]
        except Exception as e:
            return [self._make_issue(
                f"Could not analyze PDF {file_path.name}: {e}",
                severity=Severity.MODERATE,
            )]
        return []


@register_check
class PDFMissingTitle(AccessibilityCheck):
    check_id = "pdf-missing-title"
    title = "PDF missing document title"
    description = "PDFs should have a document title in metadata"
    wcag_criterion = "2.4.2"

    def check_html(self, html: str, url: str = "") -> list[AccessibilityIssue]:
        return []

    def check_file(self, file_path: Path) -> list[AccessibilityIssue]:
        if not file_path.suffix.lower() == ".pdf":
            return []
        try:
            import pikepdf
            with pikepdf.open(file_path) as pdf:
                info = pdf.docinfo if hasattr(pdf, 'docinfo') else {}
                title = str(info.get("/Title", "")).strip()
                if not title:
                    return [self._make_issue(
                        f"PDF missing document title: {file_path.name}",
                        severity=Severity.MODERATE,
                    )]
        except Exception:
            pass
        return []


@register_check
class PDFMissingLanguage(AccessibilityCheck):
    check_id = "pdf-missing-language"
    title = "PDF missing language attribute"
    description = "PDFs should specify the document language"
    wcag_criterion = "3.1.1"

    def check_html(self, html: str, url: str = "") -> list[AccessibilityIssue]:
        return []

    def check_file(self, file_path: Path) -> list[AccessibilityIssue]:
        if not file_path.suffix.lower() == ".pdf":
            return []
        try:
            import pikepdf
            with pikepdf.open(file_path) as pdf:
                catalog = pdf.Root
                lang = str(catalog.get("/Lang", "")).strip()
                if not lang:
                    return [self._make_issue(
                        f"PDF missing language attribute: {file_path.name}",
                        severity=Severity.MODERATE,
                    )]
        except Exception:
            pass
        return []


@register_check
class PDFImageOnly(AccessibilityCheck):
    check_id = "pdf-image-only"
    title = "PDF appears to be image-only"
    description = "PDFs with no extractable text are likely scanned images without OCR"
    wcag_criterion = "1.1.1"

    def check_html(self, html: str, url: str = "") -> list[AccessibilityIssue]:
        return []

    def check_file(self, file_path: Path) -> list[AccessibilityIssue]:
        if not file_path.suffix.lower() == ".pdf":
            return []
        try:
            import pikepdf
            with pikepdf.open(file_path) as pdf:
                total_text = ""
                for page in pdf.pages[:5]:  # Check first 5 pages
                    try:
                        text = page.extract_text() if hasattr(page, 'extract_text') else ""
                        total_text += text
                    except Exception:
                        # Try an alternative approach
                        pass

                if len(pdf.pages) > 0 and len(total_text.strip()) < 10:
                    return [self._make_issue(
                        f"PDF appears to be image-only (no extractable text): {file_path.name}",
                        severity=Severity.CRITICAL,
                    )]
        except Exception:
            pass
        return []
