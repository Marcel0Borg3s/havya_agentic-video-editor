"""Editor wrapper for OpenRouter mode.

The Editor uses FFmpeg tools deterministically — no LLM needed.
This wrapper calls run_editor directly (same as Gemini path).
"""

from __future__ import annotations

import logging

from src.models.schemas import EditPlan

logger = logging.getLogger(__name__)


def run_editor_openrouter(
    edit_plan: EditPlan,
    footage_index_path: str,
) -> str:
    """Run the Editor via OpenRouter mode (deterministic FFmpeg).

    Delegates to the existing run_editor which uses FFmpeg tools
    directly — no LLM involvement needed for rendering.
    """
    from src.agents.editor import run_editor

    logger.info("[editor-openrouter] Running deterministic render...")
    result = run_editor(edit_plan, footage_index_path)
    logger.info("[editor-openrouter] Render complete: %s", result)
    return result
