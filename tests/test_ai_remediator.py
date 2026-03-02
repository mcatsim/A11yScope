"""Tests for AI remediator."""
from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, MagicMock
from accessiflow.models import AccessibilityIssue, Severity
from accessiflow.ai.base import AIProvider, AIResponse
from accessiflow.remediation.ai_remediator import AIRemediator, AISuggestion


@pytest.fixture
def mock_provider():
    provider = MagicMock(spec=AIProvider)
    provider.generate = AsyncMock(return_value=AIResponse(
        content="This image lacks alt text. Add descriptive text.\nPrevention: Always add alt.",
        model="test-model", provider="test",
    ))
    provider.generate_alt_text = AsyncMock(return_value=AIResponse(
        content="A bar chart showing student enrollment from 2020 to 2025",
        model="test-model", provider="test",
    ))
    return provider


@pytest.fixture
def sample_issue():
    return AccessibilityIssue(
        check_id="alt-text-missing", title="Image missing alt text",
        description="Images must have alt text", severity=Severity.CRITICAL,
        wcag_criterion="1.1.1", element_html='<img src="chart.png">', ai_fixable=True,
    )


@pytest.mark.asyncio
async def test_explain_issue(mock_provider, sample_issue):
    remediator = AIRemediator(mock_provider)
    suggestion = await remediator.explain_issue(sample_issue)
    assert isinstance(suggestion, AISuggestion)
    assert suggestion.issue_check_id == "alt-text-missing"
    assert suggestion.explanation != ""
    mock_provider.generate.assert_called_once()


@pytest.mark.asyncio
async def test_suggest_alt_text(mock_provider):
    remediator = AIRemediator(mock_provider)
    alt_text = await remediator.suggest_alt_text("http://example.com/chart.png", "enrollment data")
    assert "enrollment" in alt_text.lower()
    mock_provider.generate_alt_text.assert_called_once()


@pytest.mark.asyncio
async def test_suggest_link_text(mock_provider):
    mock_provider.generate = AsyncMock(return_value=AIResponse(
        content="View the course syllabus\nAccess syllabus document\nOpen course syllabus",
        model="test-model", provider="test",
    ))
    remediator = AIRemediator(mock_provider)
    suggestions = await remediator.suggest_link_text('<a href="syllabus.pdf">Click here</a>', "Course info")
    assert len(suggestions) == 3
    assert all(isinstance(s, str) for s in suggestions)


@pytest.mark.asyncio
async def test_explain_issue_without_element_html(mock_provider):
    issue = AccessibilityIssue(
        check_id="heading-hierarchy", title="Heading skip",
        description="Heading levels should not skip", severity=Severity.SERIOUS,
        wcag_criterion="1.3.1",
    )
    remediator = AIRemediator(mock_provider)
    suggestion = await remediator.explain_issue(issue)
    assert suggestion.issue_check_id == "heading-hierarchy"


@pytest.mark.asyncio
async def test_suggest_alt_text_strips_quotes(mock_provider):
    mock_provider.generate_alt_text = AsyncMock(return_value=AIResponse(
        content='"A photo of students in a classroom"', model="test", provider="test",
    ))
    remediator = AIRemediator(mock_provider)
    result = await remediator.suggest_alt_text("http://example.com/img.jpg")
    assert not result.startswith('"')
    assert not result.endswith('"')
