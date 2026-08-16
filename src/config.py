"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

import os


DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


def env_model(name: str, *, default: str = DEFAULT_GEMINI_MODEL) -> str:
    """Return a configured Gemini model, ignoring blank environment values."""

    value = os.getenv(name, "").strip()
    return value or default


DIRECTOR_MODEL = env_model("GEMINI_DIRECTOR_MODEL")
REVIEWER_MODEL = env_model("GEMINI_REVIEWER_MODEL")
ANALYSIS_MODEL = env_model("GEMINI_ANALYSIS_MODEL")
EDITOR_MODEL = env_model("GEMINI_EDITOR_MODEL")
TRIM_REFINER_MODEL = env_model("GEMINI_TRIM_REFINER_MODEL")