"""Input sanitization for Canvas-sourced strings.

All content titles from Canvas are user-generated and must be
sanitized before storage to prevent stored XSS (CWE-79).
"""

import re

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_MAX_TITLE_LENGTH = 200


def sanitize_title(value: str | None, max_length: int = _MAX_TITLE_LENGTH) -> str:
    """Strip HTML tags, null bytes, normalize whitespace, truncate."""
    if not value:
        return ""
    # Remove null bytes
    text = value.replace("\x00", "")
    # Strip all HTML tags
    text = _TAG_RE.sub("", text)
    # Normalize whitespace
    text = _WHITESPACE_RE.sub(" ", text).strip()
    # Truncate
    return text[:max_length]
