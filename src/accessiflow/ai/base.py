"""AI provider abstract base class."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AIResponse:
    """Response from an AI provider."""
    content: str
    model: str
    provider: str
    usage: dict = field(default_factory=dict)  # tokens used


class AIProvider(ABC):
    """Abstract base for AI providers. All use litellm under the hood."""

    provider_name: str = ""
    default_model: str = ""

    def __init__(self, api_key: str, model: Optional[str] = None):
        self.api_key = api_key
        self.model = model or self.default_model

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> AIResponse:
        """Generate a text response."""
        ...

    @abstractmethod
    async def generate_alt_text(
        self,
        image_url: str,
        context: str = "",
    ) -> AIResponse:
        """Generate alt text for an image using vision API."""
        ...

    async def validate_key(self) -> bool:
        """Validate the API key by making a minimal request."""
        try:
            resp = await self.generate("Say 'ok'", max_tokens=5)
            return bool(resp.content)
        except Exception:
            return False
