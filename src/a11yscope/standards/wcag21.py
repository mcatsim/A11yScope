"""WCAG 2.1 Level A and AA success criteria definitions.

Contains all 50 success criteria (30 Level A + 20 Level AA) from the
Web Content Accessibility Guidelines 2.1, organized by principle.

Reference: https://www.w3.org/TR/WCAG21/
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WCAGCriterion:
    """A single WCAG 2.1 success criterion."""

    id: str
    """Success criterion number, e.g. '1.1.1'."""

    name: str
    """Human-readable name, e.g. 'Non-text Content'."""

    level: str
    """Conformance level: 'A' or 'AA'."""

    principle: str
    """WCAG principle: 'Perceivable', 'Operable', 'Understandable', or 'Robust'."""

    url: str
    """W3C Understanding document URL."""

    description: str
    """Brief description of what the criterion requires."""


# ---------------------------------------------------------------------------
# WCAG 2.1 Level A + AA success criteria (50 total)
# ---------------------------------------------------------------------------

_BASE_URL = "https://www.w3.org/WAI/WCAG21/Understanding"

WCAG_CRITERIA: dict[str, WCAGCriterion] = {
    # ===================================================================
    # Principle 1 — Perceivable (20 criteria: 13 A + 7 AA)
    # ===================================================================

    # Guideline 1.1 — Text Alternatives
    "1.1.1": WCAGCriterion(
        id="1.1.1",
        name="Non-text Content",
        level="A",
        principle="Perceivable",
        url=f"{_BASE_URL}/non-text-content",
        description=(
            "All non-text content that is presented to the user has a text "
            "alternative that serves the equivalent purpose."
        ),
    ),

    # Guideline 1.2 — Time-based Media
    "1.2.1": WCAGCriterion(
        id="1.2.1",
        name="Audio-only and Video-only (Prerecorded)",
        level="A",
        principle="Perceivable",
        url=f"{_BASE_URL}/audio-only-and-video-only-prerecorded",
        description=(
            "For prerecorded audio-only and prerecorded video-only media, "
            "an alternative is provided that presents equivalent information."
        ),
    ),
    "1.2.2": WCAGCriterion(
        id="1.2.2",
        name="Captions (Prerecorded)",
        level="A",
        principle="Perceivable",
        url=f"{_BASE_URL}/captions-prerecorded",
        description=(
            "Captions are provided for all prerecorded audio content in "
            "synchronized media."
        ),
    ),
    "1.2.3": WCAGCriterion(
        id="1.2.3",
        name="Audio Description or Media Alternative (Prerecorded)",
        level="A",
        principle="Perceivable",
        url=f"{_BASE_URL}/audio-description-or-media-alternative-prerecorded",
        description=(
            "An alternative for time-based media or audio description of the "
            "prerecorded video content is provided for synchronized media."
        ),
    ),
    "1.2.4": WCAGCriterion(
        id="1.2.4",
        name="Captions (Live)",
        level="AA",
        principle="Perceivable",
        url=f"{_BASE_URL}/captions-live",
        description=(
            "Captions are provided for all live audio content in "
            "synchronized media."
        ),
    ),
    "1.2.5": WCAGCriterion(
        id="1.2.5",
        name="Audio Description (Prerecorded)",
        level="AA",
        principle="Perceivable",
        url=f"{_BASE_URL}/audio-description-prerecorded",
        description=(
            "Audio description is provided for all prerecorded video content "
            "in synchronized media."
        ),
    ),

    # Guideline 1.3 — Adaptable
    "1.3.1": WCAGCriterion(
        id="1.3.1",
        name="Info and Relationships",
        level="A",
        principle="Perceivable",
        url=f"{_BASE_URL}/info-and-relationships",
        description=(
            "Information, structure, and relationships conveyed through "
            "presentation can be programmatically determined or are available "
            "in text."
        ),
    ),
    "1.3.2": WCAGCriterion(
        id="1.3.2",
        name="Meaningful Sequence",
        level="A",
        principle="Perceivable",
        url=f"{_BASE_URL}/meaningful-sequence",
        description=(
            "When the sequence in which content is presented affects its "
            "meaning, a correct reading sequence can be programmatically "
            "determined."
        ),
    ),
    "1.3.3": WCAGCriterion(
        id="1.3.3",
        name="Sensory Characteristics",
        level="A",
        principle="Perceivable",
        url=f"{_BASE_URL}/sensory-characteristics",
        description=(
            "Instructions provided for understanding and operating content "
            "do not rely solely on sensory characteristics of components "
            "such as shape, color, size, visual location, orientation, "
            "or sound."
        ),
    ),
    "1.3.4": WCAGCriterion(
        id="1.3.4",
        name="Orientation",
        level="AA",
        principle="Perceivable",
        url=f"{_BASE_URL}/orientation",
        description=(
            "Content does not restrict its view and operation to a single "
            "display orientation, such as portrait or landscape, unless a "
            "specific display orientation is essential."
        ),
    ),
    "1.3.5": WCAGCriterion(
        id="1.3.5",
        name="Identify Input Purpose",
        level="AA",
        principle="Perceivable",
        url=f"{_BASE_URL}/identify-input-purpose",
        description=(
            "The purpose of each input field collecting information about "
            "the user can be programmatically determined when the input "
            "field serves a purpose identified in the Input Purposes for "
            "User Interface Components section."
        ),
    ),

    # Guideline 1.4 — Distinguishable
    "1.4.1": WCAGCriterion(
        id="1.4.1",
        name="Use of Color",
        level="A",
        principle="Perceivable",
        url=f"{_BASE_URL}/use-of-color",
        description=(
            "Color is not used as the only visual means of conveying "
            "information, indicating an action, prompting a response, "
            "or distinguishing a visual element."
        ),
    ),
    "1.4.2": WCAGCriterion(
        id="1.4.2",
        name="Audio Control",
        level="A",
        principle="Perceivable",
        url=f"{_BASE_URL}/audio-control",
        description=(
            "If any audio on a Web page plays automatically for more than "
            "3 seconds, either a mechanism is available to pause or stop "
            "the audio, or a mechanism is available to control audio volume "
            "independently from the overall system volume level."
        ),
    ),
    "1.4.3": WCAGCriterion(
        id="1.4.3",
        name="Contrast (Minimum)",
        level="AA",
        principle="Perceivable",
        url=f"{_BASE_URL}/contrast-minimum",
        description=(
            "The visual presentation of text and images of text has a "
            "contrast ratio of at least 4.5:1, except for large text "
            "(at least 3:1), incidental text, or logotypes."
        ),
    ),
    "1.4.4": WCAGCriterion(
        id="1.4.4",
        name="Resize Text",
        level="AA",
        principle="Perceivable",
        url=f"{_BASE_URL}/resize-text",
        description=(
            "Except for captions and images of text, text can be resized "
            "without assistive technology up to 200 percent without loss "
            "of content or functionality."
        ),
    ),
    "1.4.5": WCAGCriterion(
        id="1.4.5",
        name="Images of Text",
        level="AA",
        principle="Perceivable",
        url=f"{_BASE_URL}/images-of-text",
        description=(
            "If the technologies being used can achieve the visual "
            "presentation, text is used to convey information rather than "
            "images of text."
        ),
    ),
    "1.4.10": WCAGCriterion(
        id="1.4.10",
        name="Reflow",
        level="AA",
        principle="Perceivable",
        url=f"{_BASE_URL}/reflow",
        description=(
            "Content can be presented without loss of information or "
            "functionality, and without requiring scrolling in two "
            "dimensions for vertical scrolling content at a width of "
            "320 CSS pixels and for horizontal scrolling content at a "
            "height of 256 CSS pixels."
        ),
    ),
    "1.4.11": WCAGCriterion(
        id="1.4.11",
        name="Non-text Contrast",
        level="AA",
        principle="Perceivable",
        url=f"{_BASE_URL}/non-text-contrast",
        description=(
            "The visual presentation of user interface components and "
            "graphical objects have a contrast ratio of at least 3:1 "
            "against adjacent colors."
        ),
    ),
    "1.4.12": WCAGCriterion(
        id="1.4.12",
        name="Text Spacing",
        level="AA",
        principle="Perceivable",
        url=f"{_BASE_URL}/text-spacing",
        description=(
            "No loss of content or functionality occurs when users override "
            "text spacing properties: line height to at least 1.5 times the "
            "font size; spacing following paragraphs to at least 2 times the "
            "font size; letter spacing to at least 0.12 times the font size; "
            "word spacing to at least 0.16 times the font size."
        ),
    ),
    "1.4.13": WCAGCriterion(
        id="1.4.13",
        name="Content on Hover or Focus",
        level="AA",
        principle="Perceivable",
        url=f"{_BASE_URL}/content-on-hover-or-focus",
        description=(
            "Where receiving and then removing pointer hover or keyboard "
            "focus triggers additional content to become visible and then "
            "hidden, the additional content is dismissible, hoverable, "
            "and persistent."
        ),
    ),

    # ===================================================================
    # Principle 2 — Operable (17 criteria: 13 A + 4 AA)
    # ===================================================================

    # Guideline 2.1 — Keyboard Accessible
    "2.1.1": WCAGCriterion(
        id="2.1.1",
        name="Keyboard",
        level="A",
        principle="Operable",
        url=f"{_BASE_URL}/keyboard",
        description=(
            "All functionality of the content is operable through a "
            "keyboard interface without requiring specific timings for "
            "individual keystrokes."
        ),
    ),
    "2.1.2": WCAGCriterion(
        id="2.1.2",
        name="No Keyboard Trap",
        level="A",
        principle="Operable",
        url=f"{_BASE_URL}/no-keyboard-trap",
        description=(
            "If keyboard focus can be moved to a component of the page "
            "using a keyboard interface, then focus can be moved away from "
            "that component using only a keyboard interface, and, if it "
            "requires more than unmodified arrow or tab keys, the user is "
            "advised of the method for moving focus."
        ),
    ),
    "2.1.4": WCAGCriterion(
        id="2.1.4",
        name="Character Key Shortcuts",
        level="A",
        principle="Operable",
        url=f"{_BASE_URL}/character-key-shortcuts",
        description=(
            "If a keyboard shortcut is implemented using only letter, "
            "punctuation, number, or symbol characters, then the shortcut "
            "can be turned off, remapped, or is only active on focus."
        ),
    ),

    # Guideline 2.2 — Enough Time
    "2.2.1": WCAGCriterion(
        id="2.2.1",
        name="Timing Adjustable",
        level="A",
        principle="Operable",
        url=f"{_BASE_URL}/timing-adjustable",
        description=(
            "For each time limit that is set by the content, the user can "
            "turn off, adjust, or extend the time limit."
        ),
    ),
    "2.2.2": WCAGCriterion(
        id="2.2.2",
        name="Pause, Stop, Hide",
        level="A",
        principle="Operable",
        url=f"{_BASE_URL}/pause-stop-hide",
        description=(
            "For moving, blinking, scrolling, or auto-updating information, "
            "the user can pause, stop, or hide it."
        ),
    ),

    # Guideline 2.3 — Seizures and Physical Reactions
    "2.3.1": WCAGCriterion(
        id="2.3.1",
        name="Three Flashes or Below Threshold",
        level="A",
        principle="Operable",
        url=f"{_BASE_URL}/three-flashes-or-below-threshold",
        description=(
            "Web pages do not contain anything that flashes more than three "
            "times in any one second period, or the flash is below the "
            "general flash and red flash thresholds."
        ),
    ),

    # Guideline 2.4 — Navigable
    "2.4.1": WCAGCriterion(
        id="2.4.1",
        name="Bypass Blocks",
        level="A",
        principle="Operable",
        url=f"{_BASE_URL}/bypass-blocks",
        description=(
            "A mechanism is available to bypass blocks of content that are "
            "repeated on multiple Web pages."
        ),
    ),
    "2.4.2": WCAGCriterion(
        id="2.4.2",
        name="Page Titled",
        level="A",
        principle="Operable",
        url=f"{_BASE_URL}/page-titled",
        description=(
            "Web pages have titles that describe topic or purpose."
        ),
    ),
    "2.4.3": WCAGCriterion(
        id="2.4.3",
        name="Focus Order",
        level="A",
        principle="Operable",
        url=f"{_BASE_URL}/focus-order",
        description=(
            "If a Web page can be navigated sequentially and the navigation "
            "sequences affect meaning or operation, focusable components "
            "receive focus in an order that preserves meaning and operability."
        ),
    ),
    "2.4.4": WCAGCriterion(
        id="2.4.4",
        name="Link Purpose (In Context)",
        level="A",
        principle="Operable",
        url=f"{_BASE_URL}/link-purpose-in-context",
        description=(
            "The purpose of each link can be determined from the link text "
            "alone or from the link text together with its programmatically "
            "determined link context."
        ),
    ),
    "2.4.5": WCAGCriterion(
        id="2.4.5",
        name="Multiple Ways",
        level="AA",
        principle="Operable",
        url=f"{_BASE_URL}/multiple-ways",
        description=(
            "More than one way is available to locate a Web page within a "
            "set of Web pages except where the Web Page is the result of, "
            "or a step in, a process."
        ),
    ),
    "2.4.6": WCAGCriterion(
        id="2.4.6",
        name="Headings and Labels",
        level="AA",
        principle="Operable",
        url=f"{_BASE_URL}/headings-and-labels",
        description=(
            "Headings and labels describe topic or purpose."
        ),
    ),
    "2.4.7": WCAGCriterion(
        id="2.4.7",
        name="Focus Visible",
        level="AA",
        principle="Operable",
        url=f"{_BASE_URL}/focus-visible",
        description=(
            "Any keyboard operable user interface has a mode of operation "
            "where the keyboard focus indicator is visible."
        ),
    ),

    # Guideline 2.5 — Input Modalities
    "2.5.1": WCAGCriterion(
        id="2.5.1",
        name="Pointer Gestures",
        level="A",
        principle="Operable",
        url=f"{_BASE_URL}/pointer-gestures",
        description=(
            "All functionality that uses multipoint or path-based gestures "
            "for operation can be operated with a single pointer without a "
            "path-based gesture, unless a multipoint or path-based gesture "
            "is essential."
        ),
    ),
    "2.5.2": WCAGCriterion(
        id="2.5.2",
        name="Pointer Cancellation",
        level="A",
        principle="Operable",
        url=f"{_BASE_URL}/pointer-cancellation",
        description=(
            "For functionality that can be operated using a single pointer, "
            "at least one of the following is true: no down-event, abort or "
            "undo, up reversal, or essential."
        ),
    ),
    "2.5.3": WCAGCriterion(
        id="2.5.3",
        name="Label in Name",
        level="A",
        principle="Operable",
        url=f"{_BASE_URL}/label-in-name",
        description=(
            "For user interface components with labels that include text or "
            "images of text, the name contains the text that is presented "
            "visually."
        ),
    ),
    "2.5.4": WCAGCriterion(
        id="2.5.4",
        name="Motion Actuation",
        level="A",
        principle="Operable",
        url=f"{_BASE_URL}/motion-actuation",
        description=(
            "Functionality that can be operated by device motion or user "
            "motion can also be operated by user interface components and "
            "responding to the motion can be disabled to prevent accidental "
            "actuation."
        ),
    ),

    # ===================================================================
    # Principle 3 — Understandable (10 criteria: 6 A + 4 AA)
    # ===================================================================

    # Guideline 3.1 — Readable
    "3.1.1": WCAGCriterion(
        id="3.1.1",
        name="Language of Page",
        level="A",
        principle="Understandable",
        url=f"{_BASE_URL}/language-of-page",
        description=(
            "The default human language of each Web page can be "
            "programmatically determined."
        ),
    ),
    "3.1.2": WCAGCriterion(
        id="3.1.2",
        name="Language of Parts",
        level="AA",
        principle="Understandable",
        url=f"{_BASE_URL}/language-of-parts",
        description=(
            "The human language of each passage or phrase in the content "
            "can be programmatically determined except for proper names, "
            "technical terms, words of indeterminate language, and words or "
            "phrases that have become part of the vernacular of the "
            "immediately surrounding text."
        ),
    ),

    # Guideline 3.2 — Predictable
    "3.2.1": WCAGCriterion(
        id="3.2.1",
        name="On Focus",
        level="A",
        principle="Understandable",
        url=f"{_BASE_URL}/on-focus",
        description=(
            "When any user interface component receives focus, it does not "
            "initiate a change of context."
        ),
    ),
    "3.2.2": WCAGCriterion(
        id="3.2.2",
        name="On Input",
        level="A",
        principle="Understandable",
        url=f"{_BASE_URL}/on-input",
        description=(
            "Changing the setting of any user interface component does not "
            "automatically cause a change of context unless the user has "
            "been advised of the behavior before using the component."
        ),
    ),
    "3.2.3": WCAGCriterion(
        id="3.2.3",
        name="Consistent Navigation",
        level="AA",
        principle="Understandable",
        url=f"{_BASE_URL}/consistent-navigation",
        description=(
            "Navigational mechanisms that are repeated on multiple Web "
            "pages within a set of Web pages occur in the same relative "
            "order each time they are repeated, unless a change is "
            "initiated by the user."
        ),
    ),
    "3.2.4": WCAGCriterion(
        id="3.2.4",
        name="Consistent Identification",
        level="AA",
        principle="Understandable",
        url=f"{_BASE_URL}/consistent-identification",
        description=(
            "Components that have the same functionality within a set of "
            "Web pages are identified consistently."
        ),
    ),

    # Guideline 3.3 — Input Assistance
    "3.3.1": WCAGCriterion(
        id="3.3.1",
        name="Error Identification",
        level="A",
        principle="Understandable",
        url=f"{_BASE_URL}/error-identification",
        description=(
            "If an input error is automatically detected, the item that is "
            "in error is identified and the error is described to the user "
            "in text."
        ),
    ),
    "3.3.2": WCAGCriterion(
        id="3.3.2",
        name="Labels or Instructions",
        level="A",
        principle="Understandable",
        url=f"{_BASE_URL}/labels-or-instructions",
        description=(
            "Labels or instructions are provided when content requires "
            "user input."
        ),
    ),
    "3.3.3": WCAGCriterion(
        id="3.3.3",
        name="Error Suggestion",
        level="AA",
        principle="Understandable",
        url=f"{_BASE_URL}/error-suggestion",
        description=(
            "If an input error is automatically detected and suggestions "
            "for correction are known, then the suggestions are provided "
            "to the user, unless it would jeopardize the security or "
            "purpose of the content."
        ),
    ),
    "3.3.4": WCAGCriterion(
        id="3.3.4",
        name="Error Prevention (Legal, Financial, Data)",
        level="AA",
        principle="Understandable",
        url=f"{_BASE_URL}/error-prevention-legal-financial-data",
        description=(
            "For Web pages that cause legal commitments or financial "
            "transactions, that modify or delete user-controllable data, "
            "or that submit user test responses, at least one of the "
            "following is true: reversible, checked, or confirmed."
        ),
    ),

    # ===================================================================
    # Principle 4 — Robust (3 criteria: 2 A + 1 AA)
    # ===================================================================

    # Guideline 4.1 — Compatible
    "4.1.1": WCAGCriterion(
        id="4.1.1",
        name="Parsing",
        level="A",
        principle="Robust",
        url=f"{_BASE_URL}/parsing",
        description=(
            "In content implemented using markup languages, elements have "
            "complete start and end tags, elements are nested according to "
            "their specifications, elements do not contain duplicate "
            "attributes, and any IDs are unique, except where the "
            "specifications allow these features. Note: this criterion is "
            "deprecated in WCAG 2.2 but remains part of WCAG 2.1."
        ),
    ),
    "4.1.2": WCAGCriterion(
        id="4.1.2",
        name="Name, Role, Value",
        level="A",
        principle="Robust",
        url=f"{_BASE_URL}/name-role-value",
        description=(
            "For all user interface components, the name and role can be "
            "programmatically determined; states, properties, and values "
            "that can be set by the user can be programmatically set; and "
            "notification of changes to these items is available to user "
            "agents, including assistive technologies."
        ),
    ),
    "4.1.3": WCAGCriterion(
        id="4.1.3",
        name="Status Messages",
        level="AA",
        principle="Robust",
        url=f"{_BASE_URL}/status-messages",
        description=(
            "In content implemented using markup languages, status messages "
            "can be programmatically determined through role or properties "
            "such that they can be presented to the user by assistive "
            "technologies without receiving focus."
        ),
    ),
}


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

def get_criterion(criterion_id: str) -> WCAGCriterion | None:
    """Look up a single WCAG criterion by its ID (e.g. '1.1.1')."""
    return WCAG_CRITERIA.get(criterion_id)


def get_criteria_by_level(level: str) -> list[WCAGCriterion]:
    """Return all criteria matching a conformance level ('A' or 'AA')."""
    return [c for c in WCAG_CRITERIA.values() if c.level == level]


def get_criteria_by_principle(principle: str) -> list[WCAGCriterion]:
    """Return all criteria under a given principle name."""
    return [c for c in WCAG_CRITERIA.values() if c.principle == principle]


# Quick sanity assertion — ensures we have exactly 50 criteria
assert len(WCAG_CRITERIA) == 50, (
    f"Expected 50 WCAG 2.1 A+AA criteria, found {len(WCAG_CRITERIA)}"
)
