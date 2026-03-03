"""Mapping from check IDs to WCAG criteria, Section 508 provisions, and best-practice URLs.

Each of the 21 accessibility checks implemented in the ``a11yscope.checks``
package is mapped to the standards it helps evaluate. This enables:

- Detailed compliance reporting per standard
- VPAT generation from audit results
- Rich issue detail pages with links to authoritative guidance
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StandardsMapping:
    """Maps a single check ID to the standards it evaluates."""

    wcag_criteria: tuple[str, ...]
    """WCAG 2.1 success criterion IDs (e.g. '1.1.1')."""

    section_508_provisions: tuple[str, ...]
    """Section 508 provision IDs (e.g. '1194.22(a)')."""

    best_practice_urls: tuple[str, ...]
    """URLs to authoritative guidance and tutorials."""


# ---------------------------------------------------------------------------
# Check ID -> Standards mapping (21 checks)
# ---------------------------------------------------------------------------

CHECK_STANDARDS_MAP: dict[str, StandardsMapping] = {

    # --- Image alt text ---

    "alt-text-missing": StandardsMapping(
        wcag_criteria=("1.1.1",),
        section_508_provisions=("1194.22(a)",),
        best_practice_urls=(
            "https://www.w3.org/WAI/tutorials/images/",
            "https://webaim.org/techniques/alttext/",
        ),
    ),

    "alt-text-nondescriptive": StandardsMapping(
        wcag_criteria=("1.1.1",),
        section_508_provisions=("1194.22(a)",),
        best_practice_urls=(
            "https://www.w3.org/WAI/tutorials/images/",
        ),
    ),

    # --- Heading structure ---

    "heading-hierarchy": StandardsMapping(
        wcag_criteria=("1.3.1", "2.4.6"),
        section_508_provisions=(),
        best_practice_urls=(
            "https://www.w3.org/WAI/tutorials/page-structure/headings/",
            "https://webaim.org/techniques/semanticstructure/",
        ),
    ),

    # --- Link text ---

    "link-text-nondescriptive": StandardsMapping(
        wcag_criteria=("2.4.4",),
        section_508_provisions=(),
        best_practice_urls=(
            "https://www.w3.org/WAI/tutorials/page-structure/links/",
            "https://webaim.org/techniques/hypertext/",
        ),
    ),

    # --- Tables ---

    "table-missing-headers": StandardsMapping(
        wcag_criteria=("1.3.1",),
        section_508_provisions=("1194.22(d)", "1194.22(g)"),
        best_practice_urls=(
            "https://www.w3.org/WAI/tutorials/tables/",
        ),
    ),

    "table-missing-caption": StandardsMapping(
        wcag_criteria=("1.3.1",),
        section_508_provisions=(),
        best_practice_urls=(
            "https://www.w3.org/WAI/tutorials/tables/",
        ),
    ),

    "table-header-missing-scope": StandardsMapping(
        wcag_criteria=("1.3.1",),
        section_508_provisions=("1194.22(g)",),
        best_practice_urls=(
            "https://www.w3.org/WAI/tutorials/tables/",
        ),
    ),

    # --- Empty interactive elements ---

    "empty-link": StandardsMapping(
        wcag_criteria=("2.4.4", "4.1.2"),
        section_508_provisions=(),
        best_practice_urls=(
            "https://www.w3.org/WAI/tutorials/page-structure/links/",
        ),
    ),

    "empty-button": StandardsMapping(
        wcag_criteria=("4.1.2",),
        section_508_provisions=(),
        best_practice_urls=(
            "https://www.w3.org/WAI/ARIA/apg/patterns/button/",
        ),
    ),

    # --- Iframes ---

    "iframe-missing-title": StandardsMapping(
        wcag_criteria=("4.1.2",),
        section_508_provisions=(),
        best_practice_urls=(
            "https://www.w3.org/WAI/WCAG21/Techniques/html/H64",
        ),
    ),

    # --- Media ---

    "media-missing-captions": StandardsMapping(
        wcag_criteria=("1.2.2",),
        section_508_provisions=("1194.22(b)",),
        best_practice_urls=(
            "https://www.w3.org/WAI/media/av/captions/",
        ),
    ),

    # --- Forms ---

    "form-input-missing-label": StandardsMapping(
        wcag_criteria=("3.3.2", "1.3.1"),
        section_508_provisions=("1194.22(n)",),
        best_practice_urls=(
            "https://www.w3.org/WAI/tutorials/forms/",
            "https://webaim.org/techniques/forms/",
        ),
    ),

    # --- Deprecated elements ---

    "deprecated-elements": StandardsMapping(
        wcag_criteria=("4.1.1",),
        section_508_provisions=(),
        best_practice_urls=(
            "https://html.spec.whatwg.org/multipage/obsolete.html",
        ),
    ),

    # --- Color contrast ---

    "color-contrast": StandardsMapping(
        wcag_criteria=("1.4.3",),
        section_508_provisions=("1194.31(b)",),
        best_practice_urls=(
            "https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum",
            "https://webaim.org/resources/contrastchecker/",
        ),
    ),

    # --- PDF checks ---

    "pdf-not-tagged": StandardsMapping(
        wcag_criteria=("1.3.1",),
        section_508_provisions=("E205.4",),
        best_practice_urls=(
            "https://www.w3.org/WAI/WCAG21/Techniques/pdf/PDF9",
            "https://pdfa.org/resource/pdfua-in-a-nutshell/",
        ),
    ),

    "pdf-missing-title": StandardsMapping(
        wcag_criteria=("2.4.2",),
        section_508_provisions=("E205.4",),
        best_practice_urls=(
            "https://www.w3.org/WAI/WCAG21/Techniques/pdf/PDF18",
        ),
    ),

    "pdf-missing-language": StandardsMapping(
        wcag_criteria=("3.1.1",),
        section_508_provisions=("E205.4",),
        best_practice_urls=(
            "https://www.w3.org/WAI/WCAG21/Techniques/pdf/PDF16",
        ),
    ),

    "pdf-image-only": StandardsMapping(
        wcag_criteria=("1.1.1", "1.3.1"),
        section_508_provisions=("1194.22(a)",),
        best_practice_urls=(
            "https://www.w3.org/WAI/WCAG21/Techniques/pdf/PDF7",
        ),
    ),

    # --- Office document checks ---

    "docx-images-missing-alt": StandardsMapping(
        wcag_criteria=("1.1.1",),
        section_508_provisions=("1194.22(a)",),
        best_practice_urls=(
            "https://support.microsoft.com/en-us/office/add-alternative-text-to-a-shape-picture-chart-smartart-graphic-or-other-object-44989b2a-903c-4d9a-b742-6a75b451c669",
        ),
    ),

    "pptx-slides-missing-titles": StandardsMapping(
        wcag_criteria=("2.4.2",),
        section_508_provisions=("602.3",),
        best_practice_urls=(
            "https://support.microsoft.com/en-us/office/add-a-slide-title-8ba55a82-c0d7-4ffe-a27a-3b5e0e2ef6f5",
        ),
    ),

    # --- Standalone image files ---

    "image-file-no-context": StandardsMapping(
        wcag_criteria=("1.1.1",),
        section_508_provisions=("1194.22(a)",),
        best_practice_urls=(
            "https://www.w3.org/WAI/tutorials/images/",
        ),
    ),

    # --- PPTX image alt text ---

    "pptx-images-missing-alt": StandardsMapping(
        wcag_criteria=("1.1.1",),
        section_508_provisions=("1194.22(a)",),
        best_practice_urls=(
            "https://support.microsoft.com/en-us/office/add-alternative-text-to-a-shape-picture-chart-smartart-graphic-or-other-object-44989b2a-903c-4d9a-b742-6a75b451c669",
        ),
    ),

    # --- Spreadsheet checks ---

    "xlsx-missing-sheet-titles": StandardsMapping(
        wcag_criteria=("2.4.2", "1.3.1"),
        section_508_provisions=("602.3",),
        best_practice_urls=(
            "https://support.microsoft.com/en-us/office/make-your-excel-documents-accessible-to-people-with-disabilities-6cc05fc5-1314-48b5-8eb3-683e49b3e593",
        ),
    ),

    "xlsx-images-missing-alt": StandardsMapping(
        wcag_criteria=("1.1.1",),
        section_508_provisions=("1194.22(a)",),
        best_practice_urls=(
            "https://support.microsoft.com/en-us/office/add-alternative-text-to-a-shape-picture-chart-smartart-graphic-or-other-object-44989b2a-903c-4d9a-b742-6a75b451c669",
        ),
    ),
}


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

def get_standards_for_check(check_id: str) -> StandardsMapping | None:
    """Return the standards mapping for a given check ID, or None."""
    return CHECK_STANDARDS_MAP.get(check_id)


def get_checks_for_criterion(criterion_id: str) -> list[str]:
    """Return all check IDs that map to a given WCAG criterion."""
    return [
        check_id
        for check_id, mapping in CHECK_STANDARDS_MAP.items()
        if criterion_id in mapping.wcag_criteria
    ]


def get_checks_for_provision(provision_id: str) -> list[str]:
    """Return all check IDs that map to a given Section 508 provision."""
    return [
        check_id
        for check_id, mapping in CHECK_STANDARDS_MAP.items()
        if provision_id in mapping.section_508_provisions
    ]
