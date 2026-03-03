"""Multi-AI provider abstraction for accessibility remediation."""
from a11yscope.ai.base import AIProvider, AIResponse
from a11yscope.ai.registry import get_provider, available_providers

__all__ = ["AIProvider", "AIResponse", "get_provider", "available_providers"]
