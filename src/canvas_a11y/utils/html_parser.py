"""BeautifulSoup HTML parsing helpers."""
from bs4 import BeautifulSoup


def parse_html(html: str) -> BeautifulSoup:
    """Parse HTML string with lxml parser."""
    return BeautifulSoup(html or "", "lxml")


def extract_text(html: str) -> str:
    """Extract plain text from HTML."""
    return parse_html(html).get_text(separator=" ", strip=True)
