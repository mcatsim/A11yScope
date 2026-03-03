"""AI provider registry and factory."""
from __future__ import annotations

from typing import Dict, List, Optional, Type

from a11yscope.ai.base import AIProvider
from a11yscope.ai.anthropic_provider import AnthropicProvider
from a11yscope.ai.openai_provider import OpenAIProvider
from a11yscope.ai.google_provider import GoogleProvider
from a11yscope.ai.grok_provider import GrokProvider

_PROVIDERS: Dict[str, Type[AIProvider]] = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "google": GoogleProvider,
    "grok": GrokProvider,
}


def get_provider(name: str, api_key: str, model: Optional[str] = None) -> AIProvider:
    """Get an AI provider instance by name."""
    cls = _PROVIDERS.get(name.lower())
    if not cls:
        raise ValueError(f"Unknown AI provider: {name}. Available: {list(_PROVIDERS.keys())}")
    return cls(api_key=api_key, model=model)


def available_providers() -> List[Dict[str, str]]:
    """Return list of available providers with their info."""
    return [
        {
            "id": name,
            "name": cls.provider_name,
            "default_model": cls.default_model,
        }
        for name, cls in _PROVIDERS.items()
    ]
