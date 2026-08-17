"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

import os

# Import OpenRouter adapter to register with ADK registry.
# noinspection PyUnresolvedReferences
import src.models.openrouter_llm  # noqa: F401

# Set to "openrouter" to use OpenRouter free models, or "gemini" for Google.
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower()

if AI_PROVIDER == "openrouter":
    DEFAULT_GEMINI_MODEL = "openrouter/" + os.getenv(
        "OPENROUTER_MODEL", "meta-llama/llama-4-scout"
    )
    FALLBACK_GEMINI_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "")
else:
    DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"
    FALLBACK_GEMINI_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-2.5-flash")


def env_model(name: str, *, default: str = DEFAULT_GEMINI_MODEL) -> str:
    """Return a configured model, ignoring blank environment values."""

    value = os.getenv(name, "").strip()
    return value or default


DIRECTOR_MODEL = env_model("GEMINI_DIRECTOR_MODEL")
REVIEWER_MODEL = env_model("GEMINI_REVIEWER_MODEL")
ANALYSIS_MODEL = env_model("GEMINI_ANALYSIS_MODEL")
EDITOR_MODEL = env_model("GEMINI_EDITOR_MODEL")
TRIM_REFINER_MODEL = env_model("GEMINI_TRIM_REFINER_MODEL")