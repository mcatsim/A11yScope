"""HTML accessibility checks (WCAG 2.1 AA)."""
from bs4 import BeautifulSoup, Tag

from accessiflow.models import AccessibilityIssue, Severity
from accessiflow.checks.base import AccessibilityCheck
from accessiflow.checks.registry import register_check

# Helper to truncate HTML snippets
def _snippet(tag: Tag, max_len: int = 200) -> str:
    s = str(tag)
    return s[:max_len] + "..." if len(s) > max_len else s


@register_check
class AltTextMissing(AccessibilityCheck):
    check_id = "alt-text-missing"
    title = "Images missing alt text"
    description = "Images must have alt attributes for screen readers"
    wcag_criterion = "1.1.1"

    def check_html(self, html: str, url: str = "") -> list[AccessibilityIssue]:
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")
        issues = []
        for img in soup.find_all("img"):
            if not img.has_attr("alt"):
                issues.append(self._make_issue(
                    f"Image missing alt attribute: {img.get('src', 'unknown')}",
                    element_html=_snippet(img),
                    severity=Severity.CRITICAL,
                    auto_fixable=True,
                    ai_fixable=True,
                ))
        return issues


@register_check
class AltTextNonDescriptive(AccessibilityCheck):
    check_id = "alt-text-nondescriptive"
    title = "Non-descriptive alt text"
    description = "Alt text should describe the image, not just be a filename"
    wcag_criterion = "1.1.1"

    NON_DESCRIPTIVE = {"image", "photo", "picture", "graphic", "img", "icon", "logo",
                       "banner", "placeholder", "untitled", "screenshot"}

    def check_html(self, html: str, url: str = "") -> list[AccessibilityIssue]:
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")
        issues = []
        for img in soup.find_all("img", alt=True):
            alt = img["alt"].strip().lower()
            # Check for filename-like alt text or generic terms
            is_filename = "." in alt and alt.rsplit(".", 1)[-1] in {"jpg", "jpeg", "png", "gif", "svg", "bmp", "webp"}
            is_generic = alt in self.NON_DESCRIPTIVE or any(alt == f"{w}.{ext}" for w in self.NON_DESCRIPTIVE for ext in ["jpg", "png"])
            if is_filename or is_generic:
                issues.append(self._make_issue(
                    f"Non-descriptive alt text: '{img['alt']}'",
                    element_html=_snippet(img),
                    severity=Severity.SERIOUS,
                    ai_fixable=True,
                ))
        return issues


@register_check
class HeadingHierarchy(AccessibilityCheck):
    check_id = "heading-hierarchy"
    title = "Heading hierarchy violations"
    description = "Headings must not skip levels (e.g., h2 followed by h4)"
    wcag_criterion = "1.3.1"

    def check_html(self, html: str, url: str = "") -> list[AccessibilityIssue]:
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")
        headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
        issues = []
        prev_level = 0
        for h in headings:
            level = int(h.name[1])
            if prev_level > 0 and level > prev_level + 1:
                issues.append(self._make_issue(
                    f"Heading level skipped: h{prev_level} → h{level}",
                    element_html=_snippet(h),
                    severity=Severity.SERIOUS,
                    auto_fixable=True,
                ))
            prev_level = level
        return issues


@register_check
class LinkTextNonDescriptive(AccessibilityCheck):
    check_id = "link-text-nondescriptive"
    title = "Non-descriptive link text"
    description = "Link text should describe the destination, not use generic phrases"
    wcag_criterion = "2.4.4"

    BAD_TEXTS = {"click here", "here", "read more", "more", "link", "this", "learn more",
                 "click", "go", "this link", "click this"}

    def check_html(self, html: str, url: str = "") -> list[AccessibilityIssue]:
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")
        issues = []
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True).lower()
            if text in self.BAD_TEXTS:
                issues.append(self._make_issue(
                    f"Non-descriptive link text: '{a.get_text(strip=True)}'",
                    element_html=_snippet(a),
                    severity=Severity.SERIOUS,
                    ai_fixable=True,
                ))
        return issues


@register_check
class TableMissingHeaders(AccessibilityCheck):
    check_id = "table-missing-headers"
    title = "Tables without header cells"
    description = "Data tables must use <th> elements for headers"
    wcag_criterion = "1.3.1"

    def check_html(self, html: str, url: str = "") -> list[AccessibilityIssue]:
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")
        issues = []
        for table in soup.find_all("table"):
            if not table.find("th"):
                issues.append(self._make_issue(
                    "Table has no header cells (<th>)",
                    element_html=_snippet(table),
                    severity=Severity.SERIOUS,
                ))
        return issues


@register_check
class TableMissingCaption(AccessibilityCheck):
    check_id = "table-missing-caption"
    title = "Tables without caption"
    description = "Data tables should have a <caption> element describing the table"
    wcag_criterion = "1.3.1"

    def check_html(self, html: str, url: str = "") -> list[AccessibilityIssue]:
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")
        issues = []
        for table in soup.find_all("table"):
            if not table.find("caption"):
                issues.append(self._make_issue(
                    "Table has no <caption> element",
                    element_html=_snippet(table),
                    severity=Severity.MODERATE,
                ))
        return issues


@register_check
class TableHeaderMissingScope(AccessibilityCheck):
    check_id = "table-header-missing-scope"
    title = "Table headers missing scope"
    description = "Table <th> elements should have a scope attribute"
    wcag_criterion = "1.3.1"

    def check_html(self, html: str, url: str = "") -> list[AccessibilityIssue]:
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")
        issues = []
        for th in soup.find_all("th"):
            if not th.has_attr("scope"):
                issues.append(self._make_issue(
                    "Table header <th> missing scope attribute",
                    element_html=_snippet(th),
                    severity=Severity.MODERATE,
                    auto_fixable=True,
                ))
        return issues


@register_check
class EmptyLinks(AccessibilityCheck):
    check_id = "empty-link"
    title = "Empty links"
    description = "Links must have discernible text content or aria-label"
    wcag_criterion = "2.4.4"

    def check_html(self, html: str, url: str = "") -> list[AccessibilityIssue]:
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")
        issues = []
        for a in soup.find_all("a"):
            text = a.get_text(strip=True)
            has_aria = a.get("aria-label", "").strip() or a.get("aria-labelledby", "").strip()
            has_img_alt = any(img.get("alt", "").strip() for img in a.find_all("img"))
            if not text and not has_aria and not has_img_alt:
                issues.append(self._make_issue(
                    "Link has no accessible text",
                    element_html=_snippet(a),
                    severity=Severity.CRITICAL,
                ))
        return issues


@register_check
class EmptyButtons(AccessibilityCheck):
    check_id = "empty-button"
    title = "Empty buttons"
    description = "Buttons must have discernible text content"
    wcag_criterion = "4.1.2"

    def check_html(self, html: str, url: str = "") -> list[AccessibilityIssue]:
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")
        issues = []
        for btn in soup.find_all("button"):
            text = btn.get_text(strip=True)
            has_aria = btn.get("aria-label", "").strip() or btn.get("aria-labelledby", "").strip()
            if not text and not has_aria:
                issues.append(self._make_issue(
                    "Button has no accessible text",
                    element_html=_snippet(btn),
                    severity=Severity.CRITICAL,
                ))
        return issues


@register_check
class IframeMissingTitle(AccessibilityCheck):
    check_id = "iframe-missing-title"
    title = "Iframes without title"
    description = "Iframes must have a title attribute describing their content"
    wcag_criterion = "4.1.2"

    def check_html(self, html: str, url: str = "") -> list[AccessibilityIssue]:
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")
        issues = []
        for iframe in soup.find_all("iframe"):
            if not iframe.get("title", "").strip():
                issues.append(self._make_issue(
                    f"Iframe missing title: {iframe.get('src', 'unknown')[:80]}",
                    element_html=_snippet(iframe),
                    severity=Severity.SERIOUS,
                ))
        return issues


@register_check
class MediaMissingCaptions(AccessibilityCheck):
    check_id = "media-missing-captions"
    title = "Media without captions"
    description = "Video and audio elements should have captions or text alternatives"
    wcag_criterion = "1.2.2"

    def check_html(self, html: str, url: str = "") -> list[AccessibilityIssue]:
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")
        issues = []
        for media in soup.find_all(["video", "audio"]):
            has_track = media.find("track", kind="captions") or media.find("track", kind="subtitles")
            if not has_track:
                issues.append(self._make_issue(
                    f"<{media.name}> element has no captions track",
                    element_html=_snippet(media),
                    severity=Severity.CRITICAL,
                ))
        return issues


@register_check
class FormInputsMissingLabels(AccessibilityCheck):
    check_id = "form-input-missing-label"
    title = "Form inputs without labels"
    description = "Form inputs must be associated with a label"
    wcag_criterion = "3.3.2"

    def check_html(self, html: str, url: str = "") -> list[AccessibilityIssue]:
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")
        issues = []
        for inp in soup.find_all(["input", "select", "textarea"]):
            if inp.get("type") in ("hidden", "submit", "button", "image"):
                continue
            inp_id = inp.get("id", "")
            has_label = bool(inp_id and soup.find("label", attrs={"for": inp_id}))
            has_aria = inp.get("aria-label", "").strip() or inp.get("aria-labelledby", "").strip()
            has_title = inp.get("title", "").strip()
            # Check if wrapped in a label
            parent_label = inp.find_parent("label")
            if not has_label and not has_aria and not has_title and not parent_label:
                issues.append(self._make_issue(
                    f"Form input has no associated label",
                    element_html=_snippet(inp),
                    severity=Severity.SERIOUS,
                ))
        return issues


@register_check
class DeprecatedElements(AccessibilityCheck):
    check_id = "deprecated-elements"
    title = "Deprecated HTML elements"
    description = "Deprecated elements like <font>, <center> should not be used"
    wcag_criterion = "508"

    DEPRECATED = {"font", "center", "marquee", "blink", "big", "strike", "tt", "u"}

    def check_html(self, html: str, url: str = "") -> list[AccessibilityIssue]:
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")
        issues = []
        for tag_name in self.DEPRECATED:
            for tag in soup.find_all(tag_name):
                issues.append(self._make_issue(
                    f"Deprecated element <{tag_name}> found",
                    element_html=_snippet(tag),
                    severity=Severity.MINOR,
                ))
        return issues
