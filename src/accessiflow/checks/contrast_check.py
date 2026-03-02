"""Color contrast accessibility check (WCAG 1.4.3)."""
import re
from bs4 import BeautifulSoup, Tag

from accessiflow.models import AccessibilityIssue, Severity
from accessiflow.checks.base import AccessibilityCheck
from accessiflow.checks.registry import register_check


# Named CSS colors subset (most common)
CSS_NAMED_COLORS = {
    "black": (0, 0, 0), "white": (255, 255, 255), "red": (255, 0, 0),
    "green": (0, 128, 0), "blue": (0, 0, 255), "yellow": (255, 255, 0),
    "gray": (128, 128, 128), "grey": (128, 128, 128), "silver": (192, 192, 192),
    "navy": (0, 0, 128), "maroon": (128, 0, 0), "purple": (128, 0, 128),
    "orange": (255, 165, 0), "pink": (255, 192, 203), "brown": (165, 42, 42),
    "cyan": (0, 255, 255), "magenta": (255, 0, 255), "lime": (0, 255, 0),
    "olive": (128, 128, 0), "teal": (0, 128, 128), "aqua": (0, 255, 255),
    "darkgray": (169, 169, 169), "darkgrey": (169, 169, 169),
    "lightgray": (211, 211, 211), "lightgrey": (211, 211, 211),
    "darkblue": (0, 0, 139), "darkred": (139, 0, 0), "darkgreen": (0, 100, 0),
}


def parse_color(color_str: str) -> tuple[int, int, int] | None:
    """Parse a CSS color string to RGB tuple."""
    if not color_str:
        return None
    color_str = color_str.strip().lower()

    # Named colors
    if color_str in CSS_NAMED_COLORS:
        return CSS_NAMED_COLORS[color_str]

    # Hex colors
    hex_match = re.match(r'^#([0-9a-f]{3,8})$', color_str)
    if hex_match:
        h = hex_match.group(1)
        if len(h) == 3:
            return tuple(int(c * 2, 16) for c in h)  # type: ignore
        elif len(h) >= 6:
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    # rgb() / rgba()
    rgb_match = re.match(r'rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)', color_str)
    if rgb_match:
        return (int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3)))

    return None


def relative_luminance(r: int, g: int, b: int) -> float:
    """Calculate relative luminance per WCAG 2.1."""
    def linearize(c: int) -> float:
        s = c / 255.0
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4
    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)


def contrast_ratio(color1: tuple[int, int, int], color2: tuple[int, int, int]) -> float:
    """Calculate WCAG contrast ratio between two colors."""
    l1 = relative_luminance(*color1)
    l2 = relative_luminance(*color2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _get_style_property(tag: Tag, prop: str) -> str | None:
    """Extract a CSS property from inline style."""
    style = tag.get("style", "")
    if not style:
        return None
    for part in str(style).split(";"):
        if ":" in part:
            key, val = part.split(":", 1)
            if key.strip().lower() == prop:
                return val.strip()
    return None


def _snippet(tag: Tag, max_len: int = 200) -> str:
    s = str(tag)
    return s[:max_len] + "..." if len(s) > max_len else s


@register_check
class ColorContrastCheck(AccessibilityCheck):
    check_id = "color-contrast"
    title = "Insufficient color contrast"
    description = "Text must have a contrast ratio of at least 4.5:1 (3:1 for large text)"
    wcag_criterion = "1.4.3"

    def check_html(self, html: str, url: str = "") -> list[AccessibilityIssue]:
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")
        issues = []

        # Check elements with inline color styles
        for tag in soup.find_all(style=True):
            fg_str = _get_style_property(tag, "color")
            bg_str = _get_style_property(tag, "background-color") or _get_style_property(tag, "background")

            if not fg_str and not bg_str:
                continue

            fg = parse_color(fg_str) if fg_str else None
            bg = parse_color(bg_str) if bg_str else None

            # If only one color is specified, assume the other is white/black
            if fg and not bg:
                bg = (255, 255, 255)  # assume white background
            elif bg and not fg:
                fg = (0, 0, 0)  # assume black text

            if fg and bg:
                ratio = contrast_ratio(fg, bg)
                # Check for large text (>=18pt or >=14pt bold)
                font_size_str = _get_style_property(tag, "font-size")
                is_large = False
                if font_size_str:
                    size_match = re.match(r'(\d+(?:\.\d+)?)\s*(px|pt|em|rem)', font_size_str)
                    if size_match:
                        size_val = float(size_match.group(1))
                        unit = size_match.group(2)
                        pt_size = size_val if unit == "pt" else size_val * 0.75 if unit == "px" else size_val * 12
                        is_large = pt_size >= 18

                threshold = 3.0 if is_large else 4.5
                if ratio < threshold:
                    issues.append(self._make_issue(
                        f"Contrast ratio {ratio:.2f}:1 below {threshold}:1 minimum",
                        element_html=_snippet(tag),
                        severity=Severity.SERIOUS,
                    ))

        # Also check <font> elements with color attribute
        for font_tag in soup.find_all("font", color=True):
            fg = parse_color(font_tag["color"])
            if fg:
                bg = (255, 255, 255)  # assume white background
                ratio = contrast_ratio(fg, bg)
                if ratio < 4.5:
                    issues.append(self._make_issue(
                        f"Font color contrast ratio {ratio:.2f}:1 below 4.5:1",
                        element_html=_snippet(font_tag),
                        severity=Severity.SERIOUS,
                    ))

        return issues
