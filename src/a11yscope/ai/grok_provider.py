"""Grok AI provider via litellm (OpenAI-compatible)."""
from __future__ import annotations

from typing import Optional
from a11yscope.ai.base import AIProvider, AIResponse


class GrokProvider(AIProvider):
    provider_name = "Grok (xAI)"
    default_model = "openai/grok-3"

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> AIResponse:
        import litellm

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await litellm.acompletion(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            api_key=self.api_key,
            api_base="https://api.x.ai/v1",
        )

        return AIResponse(
            content=response.choices[0].message.content or "",
            model=self.model,
            provider="grok",
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
            },
        )

    async def generate_alt_text(
        self,
        image_url: str,
        context: str = "",
    ) -> AIResponse:
        from a11yscope.ai.prompts import ALT_TEXT_PROMPT

        prompt = ALT_TEXT_PROMPT.format(context=context or "educational content")
        import litellm

        messages = [
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": image_url}},
                {"type": "text", "text": prompt},
            ]},
        ]

        response = await litellm.acompletion(
            model=self.model,
            messages=messages,
            max_tokens=256,
            api_key=self.api_key,
            api_base="https://api.x.ai/v1",
        )

        return AIResponse(
            content=response.choices[0].message.content or "",
            model=self.model,
            provider="grok",
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
            },
        )
