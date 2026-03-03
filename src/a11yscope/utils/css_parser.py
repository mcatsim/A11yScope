"""Inline CSS style extraction utilities."""
import re
from bs4 import Tag


def get_inline_styles(tag: Tag) -> dict[str, str]:
    """Parse inline style attribute into a dictionary."""
    style = tag.get("style", "")
    if not style:
        return {}
    result = {}
    for part in str(style).split(";"):
        if ":" in part:
            key, val = part.split(":", 1)
            result[key.strip().lower()] = val.strip()
    return result


def get_style_property(tag: Tag, prop: str) -> str | None:
    """Get a single CSS property value from inline styles."""
    styles = get_inline_styles(tag)
    return styles.get(prop)
