"""Null AI provider - for deterministic mode without LLM calls."""

from __future__ import annotations

from src.ai_provider_base import AIProvider


class NullProvider(AIProvider):
    """Provider that always raises - forces deterministic fallback."""

    def chat(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        raise RuntimeError(
            "AI is disabled (AI_PROVIDER=none). "
            "Use deterministic fallback."
        )

    def is_available(self) -> bool:
        return False
