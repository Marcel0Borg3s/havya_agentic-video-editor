"""Director agent using OpenRouter (bypasses ADK)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from src.config import AI_PROVIDER, DEFAULT_GEMINI_MODEL
from src.models.schemas import (
    CreativeBrief,
    EditPlan,
    EditPlanEntry,
    FootageIndex,
)

logger = logging.getLogger(__name__)


def _repair_json(text: str) -> dict:
    """Repair common LLM JSON issues and parse progressively."""
    cleaned = text.strip()
    # Remove markdown fences.
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    # Find opening brace.
    if not cleaned.startswith("{"):
        idx = cleaned.find("{")
        if idx >= 0:
            cleaned = cleaned[idx:]
    # Progressive parse: try each closing brace from right to left.
    for end in range(len(cleaned), 0, -1):
        if cleaned[end - 1] != "}":
            continue
        try:
            return json.loads(cleaned[:end])
        except json.JSONDecodeError:
            continue
    # Last resort.
    return json.loads(cleaned)


def _shots_to_text(shots: list) -> str:
    """Format shots for the prompt."""
    lines: list[str] = []
    for i, shot in enumerate(shots):
        transcript_preview = (shot.transcript[:120] if shot.transcript else "")
        lines.append(
            f"Shot {i}: source_file=\"{shot.source_file}\", "
            f"start_time={shot.start_time}, end_time={shot.end_time}, "
            f"description=\"{shot.description}\", "
            f"energy={shot.energy_level}, "
            f"transcript=\"{transcript_preview}\", "
            f"roll_type={shot.roll_type}"
        )
    return "\n".join(lines)


def run_director_openrouter(
    brief: CreativeBrief,
    footage_index_path: str,
) -> EditPlan:
    """Run the Director via OpenRouter without ADK tool calling.

    Reads the FootageIndex, builds a prompt with all shots, and asks
    the model to produce an EditPlan as structured JSON.
    """
    from src.ai_provider import call_openrouter

    if not Path(footage_index_path).exists():
        raise FileNotFoundError(
            f"footage_index_path does not exist: {footage_index_path}"
        )

    index = FootageIndex.model_validate_json(
        Path(footage_index_path).read_text("utf-8")
    )

    shots_text = _shots_to_text(index.shots)

    system_prompt = (
        "You are the Director agent for an AI video editor. Your job is to "
        "turn a creative brief and a list of video shots into a structured "
        "EditPlan that a downstream Editor will render.\n\n"
        "RULES:\n"
        "- You have NO tools. Work with the shots provided below.\n"
        "- Select 5-10 shots and order them to match the creative brief.\n"
        "- A-Roll shots (on-camera talent) carry narrative.\n"
        "- B-Roll shots (product, texture, environment) are visual cutaways.\n"
        "- Alternate energy levels. Start with the highest-energy shot (hook).\n"
        "- B-Roll duration does NOT count toward total_duration.\n"
        "- Only A-Roll shots count toward total_duration.\n"
        "- Target duration is in the brief. Be within ±10%.\n"
        "- shot_id format: \"source_file#start_time\" (use exact values from shots).\n"
        "- start_trim >= shot.start_time, end_trim <= shot.end_time.\n"
        "- Return ONLY valid JSON matching the DirectorOutput schema.\n"
        "- Do NOT include markdown fences, commentary, or anything else.\n"
        "- Just the raw JSON object.\n"
    )

    user_prompt = (
        "## Creative Brief\n"
        f"{brief.model_dump_json(indent=2)}\n\n"
        "## Available Shots\n"
        f"{shots_text}\n\n"
        "## Output Schema\n"
        "Return a JSON object with exactly these fields:\n"
        "- entries: array of objects, each with:\n"
        "  - shot_id: string \"source_file#start_time\"\n"
        "  - start_trim: float (seconds, relative to source file)\n"
        "  - end_trim: float (seconds, relative to source file)\n"
        "  - position: int (ordering, 0-based)\n"
        "  - text_overlay: string or null\n"
        "  - transition: string or null\n"
        "- music_path: null\n"
        "- total_duration: float (sum of A-Roll entry durations only)\n\n"
        "Produce the EditPlan JSON now:"
    )

    logger.info("[director-openrouter] Calling %s ...", DEFAULT_GEMINI_MODEL)
    result = call_openrouter(
        user_prompt,
        system=system_prompt,
        response_schema=None,  # Let the model produce raw JSON.
    )
    logger.info("[director-openrouter] Response received (%d chars)", len(result["text"]))

    parsed = _repair_json(result["text"])

    # Validate entries.
    entries: list[EditPlanEntry] = []
    for entry_data in parsed.get("entries", []):
        entries.append(EditPlanEntry(**entry_data))

    # Validate total_duration.
    total_duration = float(parsed.get("total_duration", 0.0))

    edit_plan = EditPlan(
        brief=brief,
        entries=entries,
        music_path=parsed.get("music_path"),
        total_duration=total_duration,
    )

    logger.info(
        "[director-openrouter] Plan: %d entries, %.1fs total",
        len(entries),
        total_duration,
    )
    return edit_plan
