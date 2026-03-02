"""Tests for AI provider abstraction."""
from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from accessiflow.ai.base import AIProvider, AIResponse
from accessiflow.ai.registry import get_provider, available_providers


def test_ai_response_dataclass():
    resp = AIResponse(content="hello", model="test", provider="test")
    assert resp.content == "hello"
    assert resp.usage == {}


def test_available_providers():
    providers = available_providers()
    assert len(providers) == 4
    names = {p["id"] for p in providers}
    assert names == {"anthropic", "openai", "google", "grok"}


def test_get_provider_valid():
    provider = get_provider("anthropic", api_key="test-key")
    assert provider.provider_name == "Anthropic"
    assert provider.api_key == "test-key"


def test_get_provider_custom_model():
    provider = get_provider("openai", api_key="test-key", model="gpt-4o-mini")
    assert provider.model == "gpt-4o-mini"


def test_get_provider_invalid():
    with pytest.raises(ValueError, match="Unknown AI provider"):
        get_provider("invalid", api_key="test")


def test_get_provider_case_insensitive():
    provider = get_provider("Anthropic", api_key="test-key")
    assert provider.provider_name == "Anthropic"


@pytest.mark.asyncio
async def test_anthropic_generate_mocked():
    """Test that AnthropicProvider calls litellm correctly."""
    provider = get_provider("anthropic", api_key="test-key")

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Test response"
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 5

    with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_response):
        result = await provider.generate("Test prompt", system_prompt="Be helpful")
        assert result.content == "Test response"
        assert result.provider == "anthropic"


@pytest.mark.asyncio
async def test_grok_uses_custom_api_base():
    """Test that Grok provider passes api_base to litellm."""
    provider = get_provider("grok", api_key="test-key")

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Grok response"
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 5

    with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_response) as mock_call:
        result = await provider.generate("Test")
        assert result.provider == "grok"
        # Verify api_base was passed
        mock_call.assert_called_once()
        call_kwargs = mock_call.call_args
        assert call_kwargs.kwargs.get("api_base") == "https://api.x.ai/v1"


@pytest.mark.asyncio
async def test_validate_key_success():
    """Test key validation success."""
    provider = get_provider("openai", api_key="test-key")

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "ok"
    mock_response.usage.prompt_tokens = 5
    mock_response.usage.completion_tokens = 1

    with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_response):
        assert await provider.validate_key() is True


@pytest.mark.asyncio
async def test_validate_key_failure():
    """Test key validation failure."""
    provider = get_provider("openai", api_key="bad-key")

    with patch("litellm.acompletion", new_callable=AsyncMock, side_effect=Exception("Invalid API key")):
        assert await provider.validate_key() is False
