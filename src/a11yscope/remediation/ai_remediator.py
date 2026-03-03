"""AI-powered accessibility remediation suggestions."""
from __future__ import annotations

from typing import Optional, List

from a11yscope.ai.base import AIProvider, AIResponse
from a11yscope.ai.prompts import SYSTEM_PROMPT, EXPLAIN_ISSUE_PROMPT, ALT_TEXT_PROMPT, LINK_TEXT_PROMPT
from a11yscope.models import AccessibilityIssue


class AISuggestion:
    """An AI-generated suggestion for fixing an accessibility issue."""
    def __init__(
        self,
        issue_check_id: str,
        explanation: str,
        suggested_fix: str,
        provider: str,
        model: str,
    ):
        self.issue_check_id = issue_check_id
        self.explanation = explanation
        self.suggested_fix = suggested_fix
        self.provider = provider
        self.model = model


class AIRemediator:
    """Uses an AI provider to generate remediation suggestions."""

    def __init__(self, provider: AIProvider):
        self.provider = provider

    async def explain_issue(self, issue: AccessibilityIssue) -> AISuggestion:
        """Get a plain-language explanation and fix for an issue."""
        element_context = ""
        if issue.element_html:
            element_context = f"Element HTML: {issue.element_html[:500]}"

        prompt = EXPLAIN_ISSUE_PROMPT.format(
            check_id=issue.check_id,
            title=issue.title,
            description=issue.description,
            severity=issue.severity,
            wcag_criterion=issue.wcag_criterion,
            element_context=element_context,
        )

        response = await self.provider.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            max_tokens=512,
        )

        return AISuggestion(
            issue_check_id=issue.check_id,
            explanation=response.content,
            suggested_fix=response.content,  # The response includes both
            provider=response.provider,
            model=response.model,
        )

    async def suggest_alt_text(self, image_url: str, context: str = "") -> str:
        """Generate alt text for an image."""
        response = await self.provider.generate_alt_text(image_url, context)
        return response.content.strip().strip('"').strip("'")

    async def suggest_link_text(self, link_html: str, context: str = "") -> List[str]:
        """Suggest better link text alternatives."""
        prompt = LINK_TEXT_PROMPT.format(link_html=link_html, context=context)
        response = await self.provider.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            max_tokens=256,
        )
        # Parse lines from response
        suggestions = [
            line.strip().lstrip("0123456789.-) ")
            for line in response.content.strip().split("\n")
            if line.strip() and not line.strip().startswith("#")
        ]
        return suggestions[:3]  # Max 3 suggestions
