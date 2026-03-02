"""PDF remediation via pikepdf -- add metadata, tags, and language."""
from pathlib import Path

import pikepdf


class PDFRemediator:
    """Fix PDF accessibility metadata using pikepdf."""

    def add_title(self, pdf_path: Path, title: str, output_path: Path | None = None) -> Path:
        """Add or update the document title in PDF metadata."""
        output = output_path or pdf_path
        with pikepdf.open(pdf_path) as pdf:
            with pdf.open_metadata() as meta:
                meta["dc:title"] = title
            # Also set in document info
            if pdf.docinfo is not None:
                pdf.docinfo["/Title"] = title
            # Set DisplayDocTitle
            if "/ViewerPreferences" not in pdf.Root:
                pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary()
            pdf.Root["/ViewerPreferences"]["/DisplayDocTitle"] = True
            pdf.save(str(output))
        return output

    def add_language(self, pdf_path: Path, language: str = "en", output_path: Path | None = None) -> Path:
        """Add language attribute to PDF."""
        output = output_path or pdf_path
        with pikepdf.open(pdf_path) as pdf:
            pdf.Root["/Lang"] = language
            pdf.save(str(output))
        return output

    def add_mark_info(self, pdf_path: Path, output_path: Path | None = None) -> Path:
        """Add MarkInfo to indicate the PDF is tagged (only if structure exists)."""
        output = output_path or pdf_path
        with pikepdf.open(pdf_path) as pdf:
            if "/MarkInfo" not in pdf.Root:
                pdf.Root["/MarkInfo"] = pikepdf.Dictionary({"/Marked": True})
            pdf.save(str(output))
        return output

    def remediate_full(self, pdf_path: Path, output_path: Path,
                       title: str | None = None, language: str = "en") -> Path:
        """Apply all available PDF fixes at once."""
        with pikepdf.open(pdf_path) as pdf:
            # Add language
            pdf.Root["/Lang"] = language

            # Add/update title
            if title:
                with pdf.open_metadata() as meta:
                    meta["dc:title"] = title
                if pdf.docinfo is not None:
                    pdf.docinfo["/Title"] = title
                if "/ViewerPreferences" not in pdf.Root:
                    pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary()
                pdf.Root["/ViewerPreferences"]["/DisplayDocTitle"] = True

            # Add MarkInfo if not present
            if "/MarkInfo" not in pdf.Root:
                pdf.Root["/MarkInfo"] = pikepdf.Dictionary({"/Marked": True})

            output_path.parent.mkdir(parents=True, exist_ok=True)
            pdf.save(str(output_path))

        return output_path
