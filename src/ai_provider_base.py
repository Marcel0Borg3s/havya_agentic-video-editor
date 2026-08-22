"""AI Provider abstraction layer.

Provides a unified interface for calling LLMs from different providers.
Routes based on AI_PROVIDER env var.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AIProvider(ABC):
    """Base class for AI providers."""

    @abstractmethod
    def chat(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """Send a chat message and return the response text."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is configured and reachable."""
        ...


def get_provider() -> AIProvider:
    """Get the configured AI provider based on AI_PROVIDER env var."""
    import os
    provider = os.getenv("AI_PROVIDER", "openrouter").lower()

    if provider == "none":
        from src.ai_provider_none import NullProvider
        return NullProvider()

    # Default: OpenAI-compatible (OpenRouter / OpenCode)
    from src.ai_provider import OpenAICompatibleProvider
    return OpenAICompatibleProvider()
