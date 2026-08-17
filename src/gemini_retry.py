"""Retry wrapper for Gemini API calls with automatic fallback."""

from __future__ import annotations

import time
import logging
from typing import Any, Callable, TypeVar

from src.config import FALLBACK_GEMINI_MODEL

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Transient errors that warrant a retry.
_RETRYABLE = ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "deadline_exceeded")


def _is_retryable(error: Exception) -> bool:
    msg = str(error).lower()
    return any(code in msg for code in _RETRYABLE)


def gemini_retry(
    fn: Callable[[], T],
    *,
    primary_model: str,
    max_retries: int = 3,
    base_delay: float = 5.0,
) -> T:
    """Call *fn* with automatic retry and model fallback.

    If the primary model fails with a transient error (503, 429), retry up to
    *max_retries* times with exponential backoff.  On the final attempt (or if
    the error is not retryable), switch to the fallback model and try once more.
    """
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as exc:
            last_error = exc
            if not _is_retryable(exc):
                raise
            delay = base_delay * (2 ** attempt)
            logger.warning(
                "Gemini call failed (attempt %d/%d): %s — retrying in %.0fs",
                attempt + 1,
                max_retries + 1,
                exc,
                delay,
            )
            time.sleep(delay)

    # All retries exhausted — try the fallback model once.
    if FALLBACK_GEMINI_MODEL and FALLBACK_GEMINI_MODEL != primary_model:
        logger.warning(
            "Primary model %s exhausted. Falling back to %s",
            primary_model,
            FALLBACK_GEMINI_MODEL,
        )
        try:
            return fn()
        except Exception as exc:
            logger.error("Fallback model also failed: %s", exc)
            raise exc from last_error

    raise last_error  # type: ignore[misc]
