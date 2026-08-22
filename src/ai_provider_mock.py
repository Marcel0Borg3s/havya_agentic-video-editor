"""Mock AI provider for unit tests."""

from __future__ import annotations

from typing import Any

from src.ai_provider_base import AIProvider


class MockProvider(AIProvider):
    """Returns configurable canned responses for testing."""

    def __init__(self, response: str = '{"entries": []}', delay: float = 0):
        self._response = response
        self._delay = delay
        self._calls: list[dict] = []

    def chat(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        import time
        if self._delay > 0:
            time.sleep(self._delay)
        self._calls.append({
            "prompt": prompt,
            "system": system,
            "temperature": temperature,
        })
        return self._response

    def is_available(self) -> bool:
        return True

    @property
    def calls(self) -> list[dict]:
        return list(self._calls)
