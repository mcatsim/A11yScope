"""Tests for the safe HTML auto-fix engine.

Covers:
- Heading hierarchy fixes (level gap correction)
- Table header scope attribute insertion
- Alt text placeholder insertion
- No-fix-needed scenarios (clean content, no fixable issues)
- Dry-run mode behavior
"""
import pytest

from a11yscope.remediation.autofix import AutoFixer
from a11yscope.models import ContentItem, ContentType, AccessibilityIssue, Severity


def _make_fixable_issue(check_id: str, severity: Severity = Severity.SERIOUS) -> AccessibilityIssue:
    """Create a fixable issue for the given check ID."""
    return AccessibilityIssue(
        check_id=check_id,
        title="Test",
        description="Test issue",
        severity=severity,
        wcag_criterion="1.3.1",
        auto_fixable=True,
    )


def _make_content_item(html: str, issues: list[AccessibilityIssue] | None = None) -> ContentItem:
    """Create a ContentItem with optional pre-set issues."""
    item = ContentItem(
        id=1, content_type=ContentType.PAGE, title="Test Page",
        url="https://canvas.example.com/courses/1/pages/test",
        html_content=html,
    )
    if issues:
        item.issues = issues
    return item


# ---------------------------------------------------------------------------
# Heading hierarchy fixes
# ---------------------------------------------------------------------------
class TestHeadingFix:
    def test_fixes_skipped_heading(self):
        fixer = AutoFixer(no_confirm=True)
        item = _make_content_item(
            "<h1>Title</h1><h3>Should be h2</h3>",
            [_make_fixable_issue("heading-hierarchy")],
        )
        result = fixer.fix_content_item(item)
        assert result is not None
        assert "<h2>" in result
        assert "<h3>" not in result

    def test_fixes_multiple_skips(self):
        fixer = AutoFixer(no_confirm=True)
        item = _make_content_item(
            "<h2>Section</h2><h4>Sub</h4><h6>Deep</h6>",
            [_make_fixable_issue("heading-hierarchy")],
        )
        result = fixer.fix_content_item(item)
        assert result is not None
        assert "h6" not in result

    def test_preserves_heading_content(self):
        fixer = AutoFixer(no_confirm=True)
        item = _make_content_item(
            "<h1>Title Text</h1><h3>Section Text</h3>",
            [_make_fixable_issue("heading-hierarchy")],
        )
        result = fixer.fix_content_item(item)
        assert result is not None
        assert "Title Text" in result
        assert "Section Text" in result

    def test_no_change_for_correct_hierarchy(self):
        """If headings are already correct, the fix function returns None."""
        fixer = AutoFixer(no_confirm=True)
        item = _make_content_item(
            "<h1>Title</h1><h2>Section</h2><h3>Sub</h3>",
            [_make_fixable_issue("heading-hierarchy")],
        )
        # The fix function is called but finds nothing to change because
        # the HTML is actually correct -- the issue was a false setup.
        # The fixer will return None since no changes were made.
        result = fixer.fix_content_item(item)
        assert result is None

    def test_marks_issue_as_fixed(self):
        fixer = AutoFixer(no_confirm=True)
        issue = _make_fixable_issue("heading-hierarchy")
        item = _make_content_item(
            "<h1>Title</h1><h3>Skip</h3>",
            [issue],
        )
        fixer.fix_content_item(item)
        assert issue.fixed is True
        assert issue.fix_description is not None


# ---------------------------------------------------------------------------
# Table scope fixes
# ---------------------------------------------------------------------------
class TestTableScopeFix:
    def test_adds_scope_to_th_in_thead(self):
        fixer = AutoFixer(no_confirm=True)
        item = _make_content_item(
            "<table><thead><tr><th>Name</th></tr></thead></table>",
            [_make_fixable_issue("table-header-missing-scope")],
        )
        result = fixer.fix_content_item(item)
        assert result is not None
        assert 'scope=' in result

    def test_adds_scope_col_in_thead(self):
        """Headers in <thead> should get scope='col'."""
        fixer = AutoFixer(no_confirm=True)
        item = _make_content_item(
            "<table><thead><tr><th>Name</th><th>Value</th></tr></thead>"
            "<tbody><tr><td>A</td><td>1</td></tr></tbody></table>",
            [_make_fixable_issue("table-header-missing-scope")],
        )
        result = fixer.fix_content_item(item)
        assert result is not None
        assert 'scope="col"' in result

    def test_preserves_existing_scope(self):
        """Headers that already have scope should not be modified."""
        fixer = AutoFixer(no_confirm=True)
        item = _make_content_item(
            '<table><thead><tr><th scope="col">Name</th></tr></thead></table>',
            [_make_fixable_issue("table-header-missing-scope")],
        )
        # Since the th already has scope, the fix should produce no change
        result = fixer.fix_content_item(item)
        assert result is None

    def test_multiple_th_all_get_scope(self):
        fixer = AutoFixer(no_confirm=True)
        item = _make_content_item(
            "<table><thead><tr><th>A</th><th>B</th><th>C</th></tr></thead></table>",
            [_make_fixable_issue("table-header-missing-scope")],
        )
        result = fixer.fix_content_item(item)
        assert result is not None
        assert result.count('scope=') == 3


# ---------------------------------------------------------------------------
# Alt text placeholder fixes
# ---------------------------------------------------------------------------
class TestAltTextFix:
    def test_adds_empty_alt(self):
        fixer = AutoFixer(no_confirm=True)
        item = _make_content_item(
            '<img src="photo.jpg">',
            [_make_fixable_issue("alt-text-missing")],
        )
        result = fixer.fix_content_item(item)
        assert result is not None
        assert 'alt=""' in result

    def test_does_not_overwrite_existing_alt(self):
        """Images that already have alt should not be touched."""
        fixer = AutoFixer(no_confirm=True)
        item = _make_content_item(
            '<img src="photo.jpg" alt="A photo">',
            [_make_fixable_issue("alt-text-missing")],
        )
        result = fixer.fix_content_item(item)
        # No images without alt, so fix function returns None -> no change
        assert result is None

    def test_multiple_images_all_fixed(self):
        fixer = AutoFixer(no_confirm=True)
        item = _make_content_item(
            '<img src="a.jpg"><img src="b.jpg">',
            [_make_fixable_issue("alt-text-missing")],
        )
        result = fixer.fix_content_item(item)
        assert result is not None
        assert result.count('alt=""') == 2

    def test_preserves_other_attributes(self):
        fixer = AutoFixer(no_confirm=True)
        item = _make_content_item(
            '<img src="photo.jpg" class="hero" id="main-img">',
            [_make_fixable_issue("alt-text-missing")],
        )
        result = fixer.fix_content_item(item)
        assert result is not None
        assert 'src="photo.jpg"' in result
        assert 'class="hero"' in result


# ---------------------------------------------------------------------------
# No-fix scenarios
# ---------------------------------------------------------------------------
class TestNoFixNeeded:
    def test_returns_none_for_clean_content(self):
        """Clean content with no issues should return None."""
        fixer = AutoFixer(no_confirm=True)
        item = _make_content_item("<p>Clean content</p>")
        result = fixer.fix_content_item(item)
        assert result is None

    def test_returns_none_for_no_html(self):
        """Content item with no HTML should return None."""
        fixer = AutoFixer(no_confirm=True)
        item = ContentItem(
            id=1, content_type=ContentType.PAGE, title="Empty",
            url="", html_content=None,
        )
        result = fixer.fix_content_item(item)
        assert result is None

    def test_returns_none_for_non_auto_fixable(self):
        """Issues that are not auto_fixable should not be fixed."""
        fixer = AutoFixer(no_confirm=True)
        non_fixable = AccessibilityIssue(
            check_id="link-text-nondescriptive",
            title="Bad link",
            description="Bad link text",
            severity=Severity.SERIOUS,
            wcag_criterion="2.4.4",
            auto_fixable=False,
        )
        item = _make_content_item(
            '<a href="/page">click here</a>',
            [non_fixable],
        )
        result = fixer.fix_content_item(item)
        assert result is None

    def test_returns_none_for_already_fixed_issues(self):
        """Issues already marked as fixed should be skipped."""
        fixer = AutoFixer(no_confirm=True)
        issue = _make_fixable_issue("alt-text-missing")
        issue.fixed = True
        item = _make_content_item(
            '<img src="photo.jpg">',
            [issue],
        )
        result = fixer.fix_content_item(item)
        assert result is None


# ---------------------------------------------------------------------------
# Dry-run mode
# ---------------------------------------------------------------------------
class TestDryRun:
    def test_dry_run_does_not_modify_html(self):
        """In dry_run mode, the fix is shown but not applied (returns None)."""
        fixer = AutoFixer(no_confirm=True)
        item = _make_content_item(
            "<h1>Title</h1><h3>Skip</h3>",
            [_make_fixable_issue("heading-hierarchy")],
        )
        result = fixer.fix_content_item(item, dry_run=True)
        # dry_run returns None (no HTML changes applied)
        assert result is None

    def test_dry_run_does_not_mark_fixed(self):
        fixer = AutoFixer(no_confirm=True)
        issue = _make_fixable_issue("heading-hierarchy")
        item = _make_content_item(
            "<h1>Title</h1><h3>Skip</h3>",
            [issue],
        )
        fixer.fix_content_item(item, dry_run=True)
        assert issue.fixed is False


# ---------------------------------------------------------------------------
# Multiple fixes in one item
# ---------------------------------------------------------------------------
class TestMultipleFixes:
    def test_applies_multiple_fix_types(self):
        """An item with both heading and alt-text issues should get both fixed."""
        fixer = AutoFixer(no_confirm=True)
        item = _make_content_item(
            '<h1>Title</h1><h3>Skip</h3><img src="photo.jpg">',
            [
                _make_fixable_issue("heading-hierarchy"),
                _make_fixable_issue("alt-text-missing"),
            ],
        )
        result = fixer.fix_content_item(item)
        assert result is not None
        # Heading should be fixed
        assert "<h2>" in result
        # Alt text should be added
        assert 'alt=""' in result
