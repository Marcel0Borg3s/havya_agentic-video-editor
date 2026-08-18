"""Reviewer agent using OpenRouter (bypasses ADK)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from src.models.schemas import CreativeBrief, ReviewScore

logger = logging.getLogger(__name__)


def _repair_json(text: str) -> dict:
    """Repair common LLM JSON issues and parse progressively."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    if not cleaned.startswith("{"):
        idx = cleaned.find("{")
        if idx >= 0:
            cleaned = cleaned[idx:]
    for end in range(len(cleaned), 0, -1):
        if cleaned[end - 1] != "}":
            continue
        try:
            return json.loads(cleaned[:end])
        except json.JSONDecodeError:
            continue
    return json.loads(cleaned)


def run_reviewer_openrouter(
    brief: CreativeBrief,
    video_path: str,
) -> ReviewScore:
    """Run the Reviewer via OpenRouter without ADK tool calling.

    Sends video frames to the vision model and asks it to grade the cut.
    """
    from src.ai_provider import call_openrouter

    if not Path(video_path).exists():
        raise FileNotFoundError(f"video_path does not exist: {video_path}")

    system_prompt = (
        "You are a senior creative director reviewing a finished ad against "
        "its creative brief. You watch the video (provided as frames) and "
        "grade it honestly.\n\n"
        "RULES:\n"
        "- Score each dimension as a float in [0.0, 1.0].\n"
        "- Do NOT clamp to round numbers.\n"
        "- feedback MUST be concrete and actionable.\n"
        "- Return ONLY valid JSON matching the ReviewScore schema.\n"
        "- No markdown, no commentary. Just raw JSON.\n"
    )

    user_prompt = (
        "## Creative Brief\n"
        f"{brief.model_dump_json(indent=2)}\n\n"
        "## Output Schema\n"
        "Return a JSON object with exactly these fields:\n"
        "- adherence: float [0.0-1.0] (how well the cut honors the brief)\n"
        "- pacing: float [0.0-1.0] (energy arc, hook strength, cut rhythm)\n"
        "- visual_quality: float [0.0-1.0] (composition, framing, color)\n"
        "- watchability: float [0.0-1.0] (would a viewer keep watching)\n"
        "- overall: float [0.0-1.0] (holistic judgment, not a plain average)\n"
        "- feedback: string (concrete, actionable text. If overall < 0.7, "
        "MUST include specific suggestions with timestamps or clip numbers)\n\n"
        "Grade the video now:"
    )

    logger.info("[reviewer-openrouter] Calling model for video review...")
    result = call_openrouter(
        user_prompt,
        system=system_prompt,
        video_path=video_path,
    )
    logger.info("[reviewer-openrouter] Response received (%d chars)", len(result["text"]))

    parsed = _repair_json(result["text"])

    score = ReviewScore(
        adherence=float(parsed["adherence"]),
        pacing=float(parsed["pacing"]),
        visual_quality=float(parsed["visual_quality"]),
        watchability=float(parsed["watchability"]),
        overall=float(parsed["overall"]),
        feedback=parsed.get("feedback", "No feedback provided."),
    )

    # Validate ranges.
    for field_name in ["adherence", "pacing", "visual_quality", "watchability", "overall"]:
        value = getattr(score, field_name)
        if not (0.0 <= value <= 1.0):
            raise ValueError(
                f"reviewer-openrouter: {field_name}={value} out of [0.0, 1.0]"
            )

    if not score.feedback.strip():
        raise RuntimeError("Reviewer returned empty feedback.")

    logger.info(
        "[reviewer-openrouter] Score: overall=%.2f adherence=%.2f pacing=%.2f",
        score.overall, score.adherence, score.pacing,
    )
    return score
