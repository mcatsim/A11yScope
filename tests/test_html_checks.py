"""Tests for HTML accessibility checks (WCAG 2.1 AA).

Each of the 13 HTML check classes is tested for:
- Positive detection (issue IS found on bad HTML)
- Negative detection (clean HTML yields no issues)
- Edge cases specific to each check
"""
import pytest

from a11yscope.checks.html_checks import (
    AltTextMissing,
    AltTextNonDescriptive,
    HeadingHierarchy,
    LinkTextNonDescriptive,
    TableMissingHeaders,
    TableMissingCaption,
    TableHeaderMissingScope,
    EmptyLinks,
    EmptyButtons,
    IframeMissingTitle,
    MediaMissingCaptions,
    FormInputsMissingLabels,
    DeprecatedElements,
)
from a11yscope.models import Severity


# ---------------------------------------------------------------------------
# AltTextMissing
# ---------------------------------------------------------------------------
class TestAltTextMissing:
    def test_finds_missing_alt(self):
        html = '<img src="photo.jpg">'
        issues = AltTextMissing().check_html(html)
        assert len(issues) == 1
        assert issues[0].severity == Severity.CRITICAL
        assert issues[0].check_id == "alt-text-missing"

    def test_passes_with_alt(self):
        html = '<img src="photo.jpg" alt="A photo of a campus">'
        assert AltTextMissing().check_html(html) == []

    def test_passes_empty_alt_decorative(self):
        """Empty alt is valid for decorative images per WCAG."""
        html = '<img src="spacer.gif" alt="">'
        assert AltTextMissing().check_html(html) == []

    def test_empty_html(self):
        assert AltTextMissing().check_html("") == []

    def test_no_images(self):
        html = "<p>No images here.</p>"
        assert AltTextMissing().check_html(html) == []

    def test_multiple_images_mixed(self):
        """Two missing alt, one present -- should find exactly 2 issues."""
        html = '<img src="a.jpg"><img src="b.jpg" alt="B"><img src="c.jpg">'
        issues = AltTextMissing().check_html(html)
        assert len(issues) == 2

    def test_issue_is_auto_fixable(self):
        html = '<img src="photo.jpg">'
        issues = AltTextMissing().check_html(html)
        assert issues[0].auto_fixable is True

    def test_issue_is_ai_fixable(self):
        html = '<img src="photo.jpg">'
        issues = AltTextMissing().check_html(html)
        assert issues[0].ai_fixable is True

    def test_element_html_captured(self):
        html = '<img src="photo.jpg">'
        issues = AltTextMissing().check_html(html)
        assert issues[0].element_html is not None
        assert "photo.jpg" in issues[0].element_html


# ---------------------------------------------------------------------------
# AltTextNonDescriptive
# ---------------------------------------------------------------------------
class TestAltTextNonDescriptive:
    def test_finds_filename_alt(self):
        html = '<img src="test.jpg" alt="image1.jpg">'
        issues = AltTextNonDescriptive().check_html(html)
        assert len(issues) == 1
        assert issues[0].check_id == "alt-text-nondescriptive"

    def test_finds_generic_alt_image(self):
        html = '<img src="test.jpg" alt="image">'
        issues = AltTextNonDescriptive().check_html(html)
        assert len(issues) == 1

    def test_finds_generic_alt_photo(self):
        html = '<img src="test.jpg" alt="photo">'
        issues = AltTextNonDescriptive().check_html(html)
        assert len(issues) == 1

    def test_finds_generic_alt_logo(self):
        html = '<img src="test.jpg" alt="logo">'
        issues = AltTextNonDescriptive().check_html(html)
        assert len(issues) == 1

    def test_finds_png_filename(self):
        html = '<img src="test.jpg" alt="screenshot.png">'
        issues = AltTextNonDescriptive().check_html(html)
        assert len(issues) == 1

    def test_passes_descriptive_alt(self):
        html = '<img src="test.jpg" alt="Students studying in the library">'
        assert AltTextNonDescriptive().check_html(html) == []

    def test_passes_empty_alt(self):
        """Empty alt is not flagged (that is the domain of AltTextMissing)."""
        html = '<img src="spacer.gif" alt="">'
        assert AltTextNonDescriptive().check_html(html) == []

    def test_no_alt_attribute_skipped(self):
        """Images with no alt attribute are not in scope for this check."""
        html = '<img src="photo.jpg">'
        assert AltTextNonDescriptive().check_html(html) == []

    def test_empty_html(self):
        assert AltTextNonDescriptive().check_html("") == []

    def test_severity_is_serious(self):
        html = '<img src="test.jpg" alt="image">'
        issues = AltTextNonDescriptive().check_html(html)
        assert issues[0].severity == Severity.SERIOUS


# ---------------------------------------------------------------------------
# HeadingHierarchy
# ---------------------------------------------------------------------------
class TestHeadingHierarchy:
    def test_finds_skipped_level(self):
        html = "<h1>Title</h1><h3>Skipped h2</h3>"
        issues = HeadingHierarchy().check_html(html)
        assert len(issues) == 1
        assert issues[0].auto_fixable is True

    def test_passes_sequential(self):
        html = "<h1>Title</h1><h2>Section</h2><h3>Subsection</h3>"
        assert HeadingHierarchy().check_html(html) == []

    def test_allows_same_level(self):
        html = "<h2>A</h2><h2>B</h2>"
        assert HeadingHierarchy().check_html(html) == []

    def test_allows_going_back_up(self):
        """Going from h3 back to h2 is valid heading structure."""
        html = "<h1>Title</h1><h2>Section</h2><h3>Sub</h3><h2>Next Section</h2>"
        assert HeadingHierarchy().check_html(html) == []

    def test_multiple_skips(self):
        """h1 -> h3 -> h6 should produce two violations."""
        html = "<h1>Title</h1><h3>Skip1</h3><h6>Skip2</h6>"
        issues = HeadingHierarchy().check_html(html)
        assert len(issues) == 2

    def test_no_headings(self):
        html = "<p>No headings at all</p>"
        assert HeadingHierarchy().check_html(html) == []

    def test_single_heading(self):
        html = "<h3>Just a lone heading</h3>"
        assert HeadingHierarchy().check_html(html) == []

    def test_empty_html(self):
        assert HeadingHierarchy().check_html("") == []

    def test_severity_is_serious(self):
        html = "<h1>Title</h1><h3>Skip</h3>"
        issues = HeadingHierarchy().check_html(html)
        assert issues[0].severity == Severity.SERIOUS


# ---------------------------------------------------------------------------
# LinkTextNonDescriptive
# ---------------------------------------------------------------------------
class TestLinkTextNonDescriptive:
    def test_finds_click_here(self):
        html = '<a href="/page">click here</a>'
        issues = LinkTextNonDescriptive().check_html(html)
        assert len(issues) == 1

    def test_finds_here(self):
        html = '<a href="/page">here</a>'
        issues = LinkTextNonDescriptive().check_html(html)
        assert len(issues) == 1

    def test_finds_read_more(self):
        html = '<a href="/page">read more</a>'
        issues = LinkTextNonDescriptive().check_html(html)
        assert len(issues) == 1

    def test_finds_learn_more(self):
        html = '<a href="/page">learn more</a>'
        issues = LinkTextNonDescriptive().check_html(html)
        assert len(issues) == 1

    def test_case_insensitive(self):
        html = '<a href="/page">Click Here</a>'
        issues = LinkTextNonDescriptive().check_html(html)
        assert len(issues) == 1

    def test_passes_descriptive(self):
        html = '<a href="/syllabus">View the course syllabus</a>'
        assert LinkTextNonDescriptive().check_html(html) == []

    def test_ignores_links_without_href(self):
        """Anchor tags without href are not checked."""
        html = '<a name="anchor">click here</a>'
        assert LinkTextNonDescriptive().check_html(html) == []

    def test_empty_html(self):
        assert LinkTextNonDescriptive().check_html("") == []

    def test_multiple_bad_links(self):
        html = '<a href="/a">click here</a><a href="/b">here</a>'
        issues = LinkTextNonDescriptive().check_html(html)
        assert len(issues) == 2


# ---------------------------------------------------------------------------
# TableMissingHeaders
# ---------------------------------------------------------------------------
class TestTableMissingHeaders:
    def test_finds_no_th(self):
        html = "<table><tr><td>Data</td></tr></table>"
        issues = TableMissingHeaders().check_html(html)
        assert len(issues) == 1

    def test_passes_with_th(self):
        html = "<table><tr><th>Header</th></tr><tr><td>Data</td></tr></table>"
        assert TableMissingHeaders().check_html(html) == []

    def test_passes_th_in_thead(self):
        html = "<table><thead><tr><th>Header</th></tr></thead><tbody><tr><td>Data</td></tr></tbody></table>"
        assert TableMissingHeaders().check_html(html) == []

    def test_multiple_tables_one_bad(self):
        html = (
            "<table><tr><td>No headers</td></tr></table>"
            "<table><tr><th>Has header</th></tr><tr><td>Data</td></tr></table>"
        )
        issues = TableMissingHeaders().check_html(html)
        assert len(issues) == 1

    def test_empty_html(self):
        assert TableMissingHeaders().check_html("") == []

    def test_no_tables(self):
        html = "<p>No tables</p>"
        assert TableMissingHeaders().check_html(html) == []


# ---------------------------------------------------------------------------
# TableMissingCaption
# ---------------------------------------------------------------------------
class TestTableMissingCaption:
    def test_finds_no_caption(self):
        html = "<table><tr><th>Header</th></tr></table>"
        issues = TableMissingCaption().check_html(html)
        assert len(issues) == 1
        assert issues[0].severity == Severity.MODERATE

    def test_passes_with_caption(self):
        html = "<table><caption>Grade table</caption><tr><th>Header</th></tr></table>"
        assert TableMissingCaption().check_html(html) == []

    def test_empty_html(self):
        assert TableMissingCaption().check_html("") == []

    def test_multiple_tables_all_missing(self):
        html = "<table><tr><td>A</td></tr></table><table><tr><td>B</td></tr></table>"
        issues = TableMissingCaption().check_html(html)
        assert len(issues) == 2


# ---------------------------------------------------------------------------
# TableHeaderMissingScope
# ---------------------------------------------------------------------------
class TestTableHeaderMissingScope:
    def test_finds_missing_scope(self):
        html = "<table><tr><th>Name</th></tr></table>"
        issues = TableHeaderMissingScope().check_html(html)
        assert len(issues) == 1
        assert issues[0].auto_fixable is True
        assert issues[0].severity == Severity.MODERATE

    def test_passes_with_scope(self):
        html = '<table><tr><th scope="col">Name</th></tr></table>'
        assert TableHeaderMissingScope().check_html(html) == []

    def test_passes_scope_row(self):
        html = '<table><tr><th scope="row">Name</th><td>Value</td></tr></table>'
        assert TableHeaderMissingScope().check_html(html) == []

    def test_multiple_th_missing(self):
        html = "<table><tr><th>A</th><th>B</th><th>C</th></tr></table>"
        issues = TableHeaderMissingScope().check_html(html)
        assert len(issues) == 3

    def test_empty_html(self):
        assert TableHeaderMissingScope().check_html("") == []


# ---------------------------------------------------------------------------
# EmptyLinks
# ---------------------------------------------------------------------------
class TestEmptyLinks:
    def test_finds_empty_link(self):
        html = '<a href="/page"></a>'
        issues = EmptyLinks().check_html(html)
        assert len(issues) == 1
        assert issues[0].severity == Severity.CRITICAL

    def test_passes_with_text(self):
        html = '<a href="/page">Link text</a>'
        assert EmptyLinks().check_html(html) == []

    def test_passes_with_aria_label(self):
        html = '<a href="/page" aria-label="Go to page"></a>'
        assert EmptyLinks().check_html(html) == []

    def test_passes_with_aria_labelledby(self):
        html = '<span id="lbl">Go</span><a href="/page" aria-labelledby="lbl"></a>'
        assert EmptyLinks().check_html(html) == []

    def test_passes_with_img_alt(self):
        html = '<a href="/page"><img src="icon.png" alt="Home"></a>'
        assert EmptyLinks().check_html(html) == []

    def test_fails_with_img_no_alt(self):
        """Link containing an image without alt text is still empty."""
        html = '<a href="/page"><img src="icon.png"></a>'
        issues = EmptyLinks().check_html(html)
        assert len(issues) == 1

    def test_whitespace_only_text(self):
        """Links with only whitespace should be flagged as empty."""
        html = '<a href="/page">   </a>'
        issues = EmptyLinks().check_html(html)
        assert len(issues) == 1

    def test_empty_html(self):
        assert EmptyLinks().check_html("") == []


# ---------------------------------------------------------------------------
# EmptyButtons
# ---------------------------------------------------------------------------
class TestEmptyButtons:
    def test_finds_empty_button(self):
        html = "<button></button>"
        issues = EmptyButtons().check_html(html)
        assert len(issues) == 1
        assert issues[0].severity == Severity.CRITICAL

    def test_passes_with_text(self):
        html = "<button>Submit</button>"
        assert EmptyButtons().check_html(html) == []

    def test_passes_with_aria_label(self):
        html = '<button aria-label="Close"></button>'
        assert EmptyButtons().check_html(html) == []

    def test_passes_with_aria_labelledby(self):
        html = '<span id="lbl">Go</span><button aria-labelledby="lbl"></button>'
        assert EmptyButtons().check_html(html) == []

    def test_whitespace_only(self):
        html = "<button>   </button>"
        issues = EmptyButtons().check_html(html)
        assert len(issues) == 1

    def test_empty_html(self):
        assert EmptyButtons().check_html("") == []

    def test_button_with_child_element(self):
        """Button with a span containing text is not empty."""
        html = "<button><span>OK</span></button>"
        assert EmptyButtons().check_html(html) == []


# ---------------------------------------------------------------------------
# IframeMissingTitle
# ---------------------------------------------------------------------------
class TestIframeMissingTitle:
    def test_finds_missing_title(self):
        html = '<iframe src="https://example.com"></iframe>'
        issues = IframeMissingTitle().check_html(html)
        assert len(issues) == 1
        assert issues[0].severity == Severity.SERIOUS

    def test_passes_with_title(self):
        html = '<iframe src="https://example.com" title="Embedded video"></iframe>'
        assert IframeMissingTitle().check_html(html) == []

    def test_empty_title_fails(self):
        """An iframe with title="" (empty string) should still be flagged."""
        html = '<iframe src="https://example.com" title=""></iframe>'
        issues = IframeMissingTitle().check_html(html)
        assert len(issues) == 1

    def test_whitespace_title_fails(self):
        """An iframe with a whitespace-only title should be flagged."""
        html = '<iframe src="https://example.com" title="   "></iframe>'
        issues = IframeMissingTitle().check_html(html)
        assert len(issues) == 1

    def test_empty_html(self):
        assert IframeMissingTitle().check_html("") == []

    def test_no_iframes(self):
        html = "<p>No iframes here</p>"
        assert IframeMissingTitle().check_html(html) == []


# ---------------------------------------------------------------------------
# MediaMissingCaptions
# ---------------------------------------------------------------------------
class TestMediaMissingCaptions:
    def test_finds_video_no_captions(self):
        html = '<video src="lecture.mp4"></video>'
        issues = MediaMissingCaptions().check_html(html)
        assert len(issues) == 1
        assert issues[0].severity == Severity.CRITICAL

    def test_finds_audio_no_captions(self):
        html = '<audio src="podcast.mp3"></audio>'
        issues = MediaMissingCaptions().check_html(html)
        assert len(issues) == 1

    def test_passes_with_captions_track(self):
        html = '<video src="lecture.mp4"><track kind="captions" src="caps.vtt"></video>'
        assert MediaMissingCaptions().check_html(html) == []

    def test_passes_with_subtitles_track(self):
        html = '<video src="lecture.mp4"><track kind="subtitles" src="subs.vtt"></video>'
        assert MediaMissingCaptions().check_html(html) == []

    def test_fails_with_descriptions_track_only(self):
        """A track of kind='descriptions' does not satisfy the captions requirement."""
        html = '<video src="lecture.mp4"><track kind="descriptions" src="desc.vtt"></video>'
        issues = MediaMissingCaptions().check_html(html)
        assert len(issues) == 1

    def test_empty_html(self):
        assert MediaMissingCaptions().check_html("") == []

    def test_no_media(self):
        html = "<p>No media elements</p>"
        assert MediaMissingCaptions().check_html(html) == []


# ---------------------------------------------------------------------------
# FormInputsMissingLabels
# ---------------------------------------------------------------------------
class TestFormInputsMissingLabels:
    def test_finds_missing_label(self):
        html = '<input type="text" id="name">'
        issues = FormInputsMissingLabels().check_html(html)
        assert len(issues) == 1
        assert issues[0].severity == Severity.SERIOUS

    def test_passes_with_label_for(self):
        html = '<label for="name">Name</label><input type="text" id="name">'
        assert FormInputsMissingLabels().check_html(html) == []

    def test_passes_hidden_input(self):
        html = '<input type="hidden" name="csrf">'
        assert FormInputsMissingLabels().check_html(html) == []

    def test_passes_submit_button(self):
        html = '<input type="submit" value="Go">'
        assert FormInputsMissingLabels().check_html(html) == []

    def test_passes_button_type(self):
        html = '<input type="button" value="Go">'
        assert FormInputsMissingLabels().check_html(html) == []

    def test_passes_image_type(self):
        html = '<input type="image" src="btn.png" alt="Submit">'
        assert FormInputsMissingLabels().check_html(html) == []

    def test_passes_with_aria_label(self):
        html = '<input type="text" aria-label="Search">'
        assert FormInputsMissingLabels().check_html(html) == []

    def test_passes_with_aria_labelledby(self):
        html = '<span id="lbl">Search</span><input type="text" aria-labelledby="lbl">'
        assert FormInputsMissingLabels().check_html(html) == []

    def test_passes_with_title(self):
        html = '<input type="text" title="Enter your name">'
        assert FormInputsMissingLabels().check_html(html) == []

    def test_passes_wrapped_in_label(self):
        html = "<label>Name: <input type='text'></label>"
        assert FormInputsMissingLabels().check_html(html) == []

    def test_select_missing_label(self):
        html = '<select id="color"><option>Red</option></select>'
        issues = FormInputsMissingLabels().check_html(html)
        assert len(issues) == 1

    def test_textarea_missing_label(self):
        html = '<textarea id="bio"></textarea>'
        issues = FormInputsMissingLabels().check_html(html)
        assert len(issues) == 1

    def test_empty_html(self):
        assert FormInputsMissingLabels().check_html("") == []


# ---------------------------------------------------------------------------
# DeprecatedElements
# ---------------------------------------------------------------------------
class TestDeprecatedElements:
    def test_finds_font(self):
        html = '<font color="red">Text</font>'
        issues = DeprecatedElements().check_html(html)
        assert len(issues) >= 1
        assert issues[0].severity == Severity.MINOR

    def test_finds_center(self):
        html = "<center>Centered text</center>"
        issues = DeprecatedElements().check_html(html)
        assert len(issues) >= 1

    def test_finds_marquee(self):
        html = "<marquee>Scrolling text</marquee>"
        issues = DeprecatedElements().check_html(html)
        assert len(issues) >= 1

    def test_finds_strike(self):
        html = "<strike>Struck text</strike>"
        issues = DeprecatedElements().check_html(html)
        assert len(issues) >= 1

    def test_passes_clean(self):
        html = "<p>Clean paragraph with <strong>bold</strong> text</p>"
        assert DeprecatedElements().check_html(html) == []

    def test_multiple_deprecated(self):
        html = '<font color="red">A</font><center>B</center>'
        issues = DeprecatedElements().check_html(html)
        assert len(issues) >= 2

    def test_empty_html(self):
        assert DeprecatedElements().check_html("") == []

    def test_check_id(self):
        html = '<font color="red">Text</font>'
        issues = DeprecatedElements().check_html(html)
        assert issues[0].check_id == "deprecated-elements"


# ---------------------------------------------------------------------------
# Integration: running all checks on the shared bad HTML fixture
# ---------------------------------------------------------------------------
class TestAllChecksOnBadHtml:
    """Verify that the bad HTML fixture triggers issues from multiple checks."""

    def test_bad_html_triggers_many_checks(self, sample_html_bad):
        from a11yscope.checks.registry import get_all_checks

        all_issues = []
        for check in get_all_checks():
            all_issues.extend(check.check_html(sample_html_bad))
        # The bad HTML has at least one issue per check category
        check_ids = {issue.check_id for issue in all_issues}
        expected_ids = {
            "alt-text-missing",
            "alt-text-nondescriptive",
            "heading-hierarchy",
            "link-text-nondescriptive",
            "table-missing-headers",
            "table-missing-caption",
            "table-header-missing-scope",
            "empty-link",
            "empty-button",
            "iframe-missing-title",
            "media-missing-captions",
            "form-input-missing-label",
            "deprecated-elements",
            "color-contrast",
        }
        assert expected_ids.issubset(check_ids), f"Missing check IDs: {expected_ids - check_ids}"

    def test_clean_html_triggers_no_issues(self, sample_html_clean):
        from a11yscope.checks.registry import get_all_checks

        all_issues = []
        for check in get_all_checks():
            all_issues.extend(check.check_html(sample_html_clean))
        assert all_issues == [], f"Clean HTML should produce no issues but got: {all_issues}"
