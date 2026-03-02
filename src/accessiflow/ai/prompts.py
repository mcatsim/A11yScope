"""Shared prompt templates for AI-powered remediation."""

SYSTEM_PROMPT = """You are an accessibility expert helping make educational content \
compliant with WCAG 2.1 AA, Section 508, and universal design principles. \
Your suggestions should be practical, specific, and appropriate for higher education content."""

EXPLAIN_ISSUE_PROMPT = """Explain this accessibility issue in plain language and provide a specific fix.

Issue: {check_id} — {title}
Description: {description}
Severity: {severity}
WCAG Criterion: {wcag_criterion}
{element_context}

Provide:
1. A plain-language explanation of why this is a barrier (2-3 sentences)
2. The specific fix needed (with example code if applicable)
3. How to prevent this in the future (1 sentence)

Keep your response concise and actionable."""

ALT_TEXT_PROMPT = """Describe this image for use as alt text in {context}.

Requirements:
- Be concise but descriptive (under 125 characters preferred)
- Describe the content and function, not just appearance
- If it contains text, include the text
- If it's decorative, say "decorative"
- Use plain language appropriate for educational settings

Respond with ONLY the alt text, nothing else."""

LINK_TEXT_PROMPT = """Suggest better link text for this link in an educational context.

Current link HTML: {link_html}
Surrounding context: {context}

The link text should:
- Describe the destination or purpose
- Make sense out of context
- Not use "click here", "read more", or bare URLs

Suggest 3 alternatives, one per line. Respond with ONLY the suggestions, nothing else."""
