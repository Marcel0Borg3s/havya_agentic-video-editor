"""Shared AI configuration loaded from environment variables.

Separate module to avoid circular imports between config.py and openrouter_llm.py.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

# Load .env file from project root.
load_dotenv()

# Support both old (OPENROUTER_*) and new (AI_*) env vars.
AI_API_KEY = os.getenv("AI_API_KEY", os.getenv("OPENROUTER_API_KEY", ""))
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://openrouter.ai/api/v1")
AI_MODEL_NAME = os.getenv("AI_MODEL", os.getenv("OPENROUTER_MODEL", "gpt-5.6-luna"))
AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.1"))
AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "2000"))
