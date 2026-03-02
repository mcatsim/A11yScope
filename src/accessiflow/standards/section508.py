"""Revised Section 508 provisions mapped to WCAG criteria.

The Revised Section 508 Standards (2017) incorporate WCAG 2.0 Level A and AA
by reference (36 CFR Part 1194, Appendix A). This module maps key Section 508
provisions to their corresponding WCAG criterion IDs so that audit findings
can be reported in Section 508 compliance language.

Reference: https://www.access-board.gov/ict/
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Section508Provision:
    """A single Section 508 provision."""

    id: str
    """Provision identifier, e.g. 'E205.4' or '1194.22(a)'."""

    name: str
    """Short human-readable name of the provision."""

    description: str
    """Description of what the provision requires."""

    wcag_criteria: tuple[str, ...]
    """WCAG 2.0/2.1 criterion IDs this provision maps to."""


# ---------------------------------------------------------------------------
# Revised Section 508 provisions
# ---------------------------------------------------------------------------

SECTION_508_PROVISIONS: dict[str, Section508Provision] = {

    # --- Chapter 2: Scoping Requirements ---

    "E205.4": Section508Provision(
        id="E205.4",
        name="Accessibility Standard",
        description=(
            "Electronic content shall conform to Level A and Level AA "
            "Success Criteria and Conformance Requirements in WCAG 2.0 "
            "(W3C Recommendation 11 December 2008). This is the primary "
            "incorporation-by-reference provision."
        ),
        wcag_criteria=(
            "1.1.1", "1.2.1", "1.2.2", "1.2.3", "1.2.4", "1.2.5",
            "1.3.1", "1.3.2", "1.3.3",
            "1.4.1", "1.4.2", "1.4.3", "1.4.4", "1.4.5",
            "2.1.1", "2.1.2",
            "2.2.1", "2.2.2",
            "2.3.1",
            "2.4.1", "2.4.2", "2.4.3", "2.4.4", "2.4.5", "2.4.6", "2.4.7",
            "3.1.1", "3.1.2",
            "3.2.1", "3.2.2", "3.2.3", "3.2.4",
            "3.3.1", "3.3.2", "3.3.3", "3.3.4",
            "4.1.1", "4.1.2",
        ),
    ),

    # --- Chapter 6: Support Documentation and Services ---

    "602.3": Section508Provision(
        id="602.3",
        name="Electronic Support Documentation",
        description=(
            "Documentation in electronic format, including Web-based "
            "self-service support, shall conform to Level A and Level AA "
            "Success Criteria and Conformance Requirements in WCAG 2.0."
        ),
        wcag_criteria=(
            "1.1.1", "1.3.1", "2.4.2", "2.4.6", "3.1.1", "4.1.2",
        ),
    ),

    # --- Original Section 508 (1194.22) provisions ---
    # These are from the original 1998 standard. They are still commonly
    # referenced in procurement language and ACRs/VPATs even though the
    # Revised Section 508 supersedes them with WCAG 2.0 by reference.

    "1194.22(a)": Section508Provision(
        id="1194.22(a)",
        name="Text Equivalents for Images",
        description=(
            "A text equivalent for every non-text element shall be "
            "provided (e.g., via 'alt', 'longdesc', or in element content)."
        ),
        wcag_criteria=("1.1.1",),
    ),

    "1194.22(b)": Section508Provision(
        id="1194.22(b)",
        name="Multimedia Alternatives",
        description=(
            "Equivalent alternatives for any multimedia presentation shall "
            "be synchronized with the presentation."
        ),
        wcag_criteria=("1.2.1", "1.2.2", "1.2.3"),
    ),

    "1194.22(d)": Section508Provision(
        id="1194.22(d)",
        name="Data Tables",
        description=(
            "Row and column headers shall be identified for data tables."
        ),
        wcag_criteria=("1.3.1",),
    ),

    "1194.22(g)": Section508Provision(
        id="1194.22(g)",
        name="Row and Column Headers",
        description=(
            "Row and column headers shall be identified for data tables."
        ),
        wcag_criteria=("1.3.1",),
    ),

    "1194.22(j)": Section508Provision(
        id="1194.22(j)",
        name="Flickering",
        description=(
            "Pages shall be designed to avoid causing the screen to "
            "flicker with a frequency greater than 2 Hz and lower than "
            "55 Hz."
        ),
        wcag_criteria=("2.3.1",),
    ),

    "1194.22(l)": Section508Provision(
        id="1194.22(l)",
        name="Scripting Accessibility",
        description=(
            "When pages utilize scripting languages to display content or "
            "create interface elements, the information provided by the "
            "script shall be identified with functional text that can be "
            "read by assistive technology."
        ),
        wcag_criteria=("4.1.2",),
    ),

    "1194.22(n)": Section508Provision(
        id="1194.22(n)",
        name="Electronic Forms",
        description=(
            "When electronic forms are designed to be completed on-line, "
            "the form shall allow people using assistive technology to "
            "access the information, field elements, and functionality "
            "required for completion and submission of the form, including "
            "all directions and cues."
        ),
        wcag_criteria=("1.3.1", "3.3.2", "4.1.2"),
    ),

    # --- Functional Performance Criteria (1194.31) ---

    "1194.31(a)": Section508Provision(
        id="1194.31(a)",
        name="Functional Performance: Vision",
        description=(
            "At least one mode of operation and information retrieval that "
            "does not require user vision shall be provided, or support for "
            "assistive technology used by people who are blind shall be "
            "provided."
        ),
        wcag_criteria=("1.1.1", "1.3.1", "4.1.2"),
    ),

    "1194.31(b)": Section508Provision(
        id="1194.31(b)",
        name="Functional Performance: Limited Vision",
        description=(
            "At least one mode of operation and information retrieval that "
            "enhances visual acuity shall be provided for users with "
            "limited vision. This includes adequate color contrast and "
            "text resizing support."
        ),
        wcag_criteria=("1.4.3", "1.4.4"),
    ),

    "1194.31(c)": Section508Provision(
        id="1194.31(c)",
        name="Functional Performance: No Perception of Color",
        description=(
            "At least one mode of operation and information retrieval that "
            "does not require user perception of color shall be provided."
        ),
        wcag_criteria=("1.4.1",),
    ),
}


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

def get_provision(provision_id: str) -> Section508Provision | None:
    """Look up a single Section 508 provision by its ID."""
    return SECTION_508_PROVISIONS.get(provision_id)


def get_provisions_for_wcag(criterion_id: str) -> list[Section508Provision]:
    """Return all Section 508 provisions that reference a WCAG criterion."""
    return [
        p for p in SECTION_508_PROVISIONS.values()
        if criterion_id in p.wcag_criteria
    ]
