"""Claude AI-powered accessibility remediation."""
import base64
from pathlib import Path

import anthropic

from canvas_a11y.models import AccessibilityIssue, ContentItem


class AIRemediator:
    """Uses Claude to generate alt text, improve link text, and analyze documents."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def generate_alt_text(self, image_url: str | None = None, image_path: Path | None = None,
                          surrounding_context: str = "") -> str:
        """Generate descriptive alt text for an image using Claude vision."""
        messages_content = []

        if image_path and image_path.exists():
            # Local file — encode as base64
            import mimetypes
            media_type = mimetypes.guess_type(str(image_path))[0] or "image/png"
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
            messages_content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_data,
                },
            })
        elif image_url:
            messages_content.append({
                "type": "image",
                "source": {
                    "type": "url",
                    "url": image_url,
                },
            })
        else:
            return ""

        context_note = f"\n\nContext where this image appears: {surrounding_context}" if surrounding_context else ""
        messages_content.append({
            "type": "text",
            "text": (
                "Generate concise, descriptive alt text for this image following WCAG 2.1 guidelines. "
                "The alt text should:\n"
                "- Describe the content and function of the image\n"
                "- Be concise (under 125 characters if possible)\n"
                "- Not start with 'Image of' or 'Picture of'\n"
                "- Convey the same information a sighted user would get\n"
                f"{context_note}\n\n"
                "Return ONLY the alt text, nothing else."
            ),
        })

        response = self.client.messages.create(
            model=self.model,
            max_tokens=200,
            messages=[{"role": "user", "content": messages_content}],
        )
        return response.content[0].text.strip().strip('"')

    def improve_link_text(self, current_text: str, href: str, surrounding_html: str) -> str:
        """Generate descriptive link text to replace generic text like 'click here'."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=100,
            messages=[{
                "role": "user",
                "content": (
                    f"A link currently has the non-descriptive text '{current_text}' "
                    f"and points to: {href}\n\n"
                    f"Surrounding HTML context:\n{surrounding_html[:500]}\n\n"
                    "Generate a short, descriptive link text (2-6 words) that describes "
                    "where the link goes or what it does. Follow WCAG 2.4.4 guidelines.\n\n"
                    "Return ONLY the new link text, nothing else."
                ),
            }],
        )
        return response.content[0].text.strip().strip('"')

    def analyze_pdf_content(self, pdf_path: Path) -> dict:
        """Analyze a PDF's content for accessibility issues using Claude."""
        # Read first few pages as text for analysis
        text_content = ""
        try:
            import pikepdf
            with pikepdf.open(pdf_path) as pdf:
                for page in pdf.pages[:3]:
                    try:
                        text_content += page.extract_text() if hasattr(page, 'extract_text') else ""
                    except Exception:
                        pass
        except Exception:
            pass

        if not text_content.strip():
            return {
                "has_text": False,
                "recommendation": "This PDF appears to be image-only. Consider running OCR and adding proper tags.",
                "suggested_title": pdf_path.stem.replace("-", " ").replace("_", " ").title(),
            }

        response = self.client.messages.create(
            model=self.model,
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": (
                    f"Analyze this document content for accessibility:\n\n"
                    f"{text_content[:2000]}\n\n"
                    "Provide:\n"
                    "1. A suggested document title (if not obvious)\n"
                    "2. The document's language (e.g., 'en', 'es')\n"
                    "3. A brief accessibility recommendation\n\n"
                    "Format as:\nTitle: ...\nLanguage: ...\nRecommendation: ..."
                ),
            }],
        )

        result_text = response.content[0].text
        result = {"has_text": True, "raw_analysis": result_text}

        for line in result_text.split("\n"):
            if line.startswith("Title:"):
                result["suggested_title"] = line.split(":", 1)[1].strip()
            elif line.startswith("Language:"):
                result["suggested_language"] = line.split(":", 1)[1].strip()
            elif line.startswith("Recommendation:"):
                result["recommendation"] = line.split(":", 1)[1].strip()

        return result
