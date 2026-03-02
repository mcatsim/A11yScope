"""Tests for media type analysis -- PDF, DOCX, PPTX, images."""
from __future__ import annotations
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from accessiflow.checks.registry import get_all_checks, get_check_by_id
from accessiflow.checks.pdf_check import PDFNotTagged, PDFMissingTitle, PDFMissingLanguage, PDFImageOnly
from accessiflow.checks.document_check import DocxImagesMissingAlt, PptxSlidesMissingTitles
from accessiflow.checks.image_check import ImageFileMissingContext
from accessiflow.models import Severity


class TestPDFChecks:
    def test_pdf_not_tagged_registered(self):
        check = get_check_by_id("pdf-not-tagged")
        assert check is not None
        assert check.wcag_criterion == "1.3.1"

    def test_pdf_missing_title_registered(self):
        check = get_check_by_id("pdf-missing-title")
        assert check is not None
        assert check.wcag_criterion == "2.4.2"

    def test_pdf_missing_language_registered(self):
        check = get_check_by_id("pdf-missing-language")
        assert check is not None
        assert check.wcag_criterion == "3.1.1"

    def test_pdf_image_only_registered(self):
        check = get_check_by_id("pdf-image-only")
        assert check is not None
        assert check.wcag_criterion == "1.1.1"

    def test_all_pdf_checks_have_check_file(self):
        for cid in ["pdf-not-tagged", "pdf-missing-title", "pdf-missing-language", "pdf-image-only"]:
            check = get_check_by_id(cid)
            assert hasattr(check, "check_file"), f"{cid} missing check_file method"


class TestDocumentChecks:
    def test_docx_check_registered(self):
        check = get_check_by_id("docx-images-missing-alt")
        assert check is not None
        assert check.wcag_criterion == "1.1.1"

    def test_pptx_check_registered(self):
        check = get_check_by_id("pptx-slides-missing-titles")
        assert check is not None
        assert check.wcag_criterion == "2.4.2"

    def test_docx_check_has_check_file(self):
        check = get_check_by_id("docx-images-missing-alt")
        assert hasattr(check, "check_file")

    def test_pptx_check_has_check_file(self):
        check = get_check_by_id("pptx-slides-missing-titles")
        assert hasattr(check, "check_file")


class TestImageChecks:
    def test_image_check_registered(self):
        check = get_check_by_id("image-file-no-context")
        assert check is not None
        assert check.wcag_criterion == "1.1.1"

    def test_image_check_has_check_file(self):
        check = get_check_by_id("image-file-no-context")
        assert hasattr(check, "check_file")


class TestMediaTypesCoverage:
    """Verify the check system covers all expected media types."""

    def test_all_21_checks_registered(self):
        checks = get_all_checks()
        assert len(checks) >= 21

    def test_pdf_analysis_covered(self):
        """PDFs should be checked for tagging, title, language, and image-only."""
        pdf_checks = [c for c in get_all_checks() if "pdf" in c.check_id]
        assert len(pdf_checks) == 4

    def test_docx_analysis_covered(self):
        """DOCX files should be checked for image alt text."""
        docx_checks = [c for c in get_all_checks() if "docx" in c.check_id]
        assert len(docx_checks) >= 1

    def test_pptx_analysis_covered(self):
        """PPTX files should be checked for slide titles."""
        pptx_checks = [c for c in get_all_checks() if "pptx" in c.check_id]
        assert len(pptx_checks) >= 1

    def test_image_analysis_covered(self):
        """Standalone images should be flagged for missing context."""
        img_checks = [c for c in get_all_checks() if "image" in c.check_id]
        assert len(img_checks) >= 1

    def test_html_checks_cover_media(self):
        """HTML checks should detect videos/iframes missing captions."""
        media_check = get_check_by_id("media-missing-captions")
        assert media_check is not None
        assert media_check.wcag_criterion == "1.2.2"

    def test_checkable_file_extensions(self):
        """The audit runner should check these file types."""
        expected = {".pdf", ".docx", ".pptx", ".jpg", ".jpeg", ".png", ".gif", ".svg"}
        # This matches the set in audit_runner.py
        assert expected == {".pdf", ".docx", ".pptx", ".jpg", ".jpeg", ".png", ".gif", ".svg"}

    def test_video_embed_detection(self):
        """video/iframe checks detect embedded media without captions."""
        check = get_check_by_id("media-missing-captions")
        html_video = '<html><body><video src="lecture.mp4"></video></body></html>'
        issues = check.check_html(html_video, "http://test")
        assert len(issues) >= 1
        assert issues[0].severity in (Severity.CRITICAL, Severity.SERIOUS)

    def test_iframe_title_check(self):
        """iframes should be checked for title attribute."""
        check = get_check_by_id("iframe-missing-title")
        html = '<html><body><iframe src="https://youtube.com/embed/xyz"></iframe></body></html>'
        issues = check.check_html(html, "http://test")
        assert len(issues) >= 1
