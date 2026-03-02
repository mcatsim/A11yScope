"""Comprehensive tests for standards mapping modules."""
from __future__ import annotations
import pytest
from accessiflow.standards.wcag21 import WCAG_CRITERIA, WCAGCriterion, get_criterion, get_criteria_by_level, get_criteria_by_principle
from accessiflow.standards.section508 import SECTION_508_PROVISIONS, get_provision, get_provisions_for_wcag
from accessiflow.standards.mapping import CHECK_STANDARDS_MAP, get_standards_for_check, get_checks_for_criterion


class TestWCAGCriteria:
    def test_total_criteria_count(self):
        assert len(WCAG_CRITERIA) == 50

    def test_level_a_count(self):
        level_a = [c for c in WCAG_CRITERIA.values() if c.level == "A"]
        assert len(level_a) == 30

    def test_level_aa_count(self):
        level_aa = [c for c in WCAG_CRITERIA.values() if c.level == "AA"]
        assert len(level_aa) == 20

    def test_all_principles_present(self):
        principles = {c.principle for c in WCAG_CRITERIA.values()}
        assert principles == {"Perceivable", "Operable", "Understandable", "Robust"}

    def test_perceivable_count(self):
        p = [c for c in WCAG_CRITERIA.values() if c.principle == "Perceivable"]
        assert len(p) == 20

    def test_operable_count(self):
        o = [c for c in WCAG_CRITERIA.values() if c.principle == "Operable"]
        assert len(o) == 17

    def test_understandable_count(self):
        u = [c for c in WCAG_CRITERIA.values() if c.principle == "Understandable"]
        assert len(u) == 10

    def test_robust_count(self):
        r = [c for c in WCAG_CRITERIA.values() if c.principle == "Robust"]
        assert len(r) == 3

    def test_criterion_has_url(self):
        for cid, c in WCAG_CRITERIA.items():
            assert c.url.startswith("https://www.w3.org/"), f"{cid} has invalid URL"

    def test_criterion_has_description(self):
        for cid, c in WCAG_CRITERIA.items():
            assert len(c.description) > 10, f"{cid} has empty description"

    def test_get_criterion_existing(self):
        c = get_criterion("1.1.1")
        assert c is not None
        assert c.name == "Non-text Content"

    def test_get_criterion_nonexistent(self):
        assert get_criterion("99.99.99") is None

    def test_get_criteria_by_level(self):
        aa = get_criteria_by_level("AA")
        assert len(aa) == 20
        assert all(c.level == "AA" for c in aa)

    def test_get_criteria_by_principle(self):
        robust = get_criteria_by_principle("Robust")
        assert len(robust) == 3
        assert all(c.principle == "Robust" for c in robust)

    def test_key_criteria_present(self):
        """Verify the most commonly referenced criteria exist."""
        keys = ["1.1.1", "1.2.2", "1.3.1", "1.4.3", "2.4.2", "2.4.4", "3.1.1", "3.3.2", "4.1.2"]
        for k in keys:
            assert k in WCAG_CRITERIA, f"Missing criterion {k}"


class TestSection508:
    def test_provisions_not_empty(self):
        assert len(SECTION_508_PROVISIONS) > 0

    def test_e205_4_exists(self):
        assert "E205.4" in SECTION_508_PROVISIONS

    def test_each_provision_has_wcag_mapping(self):
        for pid, p in SECTION_508_PROVISIONS.items():
            assert len(p.wcag_criteria) > 0 or pid == "E205.4", f"{pid} has no WCAG mapping"

    def test_get_provision(self):
        p = get_provision("E205.4")
        assert p is not None
        assert "Accessibility" in p.name or "accessibility" in p.name.lower() or "WCAG" in p.description


class TestStandardsMapping:
    def test_all_checks_mapped(self):
        expected_checks = [
            "alt-text-missing", "alt-text-nondescriptive", "heading-hierarchy",
            "link-text-nondescriptive", "table-missing-headers", "table-missing-caption",
            "table-header-missing-scope", "empty-link", "empty-button",
            "iframe-missing-title", "media-missing-captions", "form-input-missing-label",
            "deprecated-elements", "color-contrast", "pdf-not-tagged",
            "pdf-missing-title", "pdf-missing-language", "pdf-image-only",
            "docx-images-missing-alt", "pptx-slides-missing-titles", "image-file-no-context",
            "pptx-images-missing-alt", "xlsx-missing-sheet-titles", "xlsx-images-missing-alt",
        ]
        for check_id in expected_checks:
            assert check_id in CHECK_STANDARDS_MAP, f"Missing mapping for {check_id}"

    def test_each_mapping_has_wcag(self):
        for check_id, m in CHECK_STANDARDS_MAP.items():
            assert len(m.wcag_criteria) > 0, f"{check_id} has no WCAG criteria"

    def test_each_mapping_has_best_practice_urls(self):
        for check_id, m in CHECK_STANDARDS_MAP.items():
            assert len(m.best_practice_urls) > 0, f"{check_id} has no best practice URLs"

    def test_urls_are_valid(self):
        for check_id, m in CHECK_STANDARDS_MAP.items():
            for url in m.best_practice_urls:
                assert url.startswith("https://"), f"{check_id} has invalid URL: {url}"

    def test_get_standards_for_check(self):
        m = get_standards_for_check("alt-text-missing")
        assert m is not None
        assert "1.1.1" in m.wcag_criteria

    def test_get_standards_for_unknown_check(self):
        assert get_standards_for_check("nonexistent") is None

    def test_reverse_lookup_criterion(self):
        checks = get_checks_for_criterion("1.1.1")
        assert "alt-text-missing" in checks

    def test_alt_text_maps_to_111(self):
        m = CHECK_STANDARDS_MAP["alt-text-missing"]
        assert "1.1.1" in m.wcag_criteria

    def test_contrast_maps_to_143(self):
        m = CHECK_STANDARDS_MAP["color-contrast"]
        assert "1.4.3" in m.wcag_criteria

    def test_pdf_checks_have_508(self):
        for check_id in ["pdf-not-tagged", "pdf-missing-title", "pdf-missing-language"]:
            m = CHECK_STANDARDS_MAP[check_id]
            assert len(m.section_508_provisions) > 0, f"{check_id} missing 508 provisions"
