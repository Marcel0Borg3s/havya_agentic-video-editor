"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

import os


DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"

# Fallback model used when the primary model is unavailable (503/429).
FALLBACK_GEMINI_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-2.5-preview")


def env_model(name: str, *, default: str = DEFAULT_GEMINI_MODEL) -> str:
    """Return a configured Gemini model, ignoring blank environment values."""

    value = os.getenv(name, "").strip()
    return value or default


DIRECTOR_MODEL = env_model("GEMINI_DIRECTOR_MODEL")
REVIEWER_MODEL = env_model("GEMINI_REVIEWER_MODEL")
ANALYSIS_MODEL = env_model("GEMINI_ANALYSIS_MODEL")
EDITOR_MODEL = env_model("GEMINI_EDITOR_MODEL")
TRIM_REFINER_MODEL = env_model("GEMINI_TRIM_REFINER_MODEL")