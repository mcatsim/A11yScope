# tests/test_sanitize.py
from a11yscope.sanitize import sanitize_title


def test_strips_html_tags():
    assert sanitize_title("<b>Bold</b> text") == "Bold text"


def test_strips_script_tags():
    assert "script" not in sanitize_title('<script>alert("xss")</script>Hello')
    assert "Hello" in sanitize_title('<script>alert("xss")</script>Hello')


def test_truncates_to_max_length():
    long_title = "A" * 300
    result = sanitize_title(long_title)
    assert len(result) == 200


def test_strips_null_bytes():
    assert sanitize_title("Hello\x00World") == "HelloWorld"


def test_normalizes_whitespace():
    assert sanitize_title("  too   many   spaces  ") == "too many spaces"


def test_empty_string():
    assert sanitize_title("") == ""
    assert sanitize_title(None) == ""
