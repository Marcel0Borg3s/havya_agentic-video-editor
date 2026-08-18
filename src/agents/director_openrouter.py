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
    """Repair common LLM JSON issues and parse progressively.

    Handles: markdown fences, inlined tool calls before JSON,
    trailing text after JSON, missing braces.
    """
    cleaned = text.strip()

    # Remove markdown fences.
    if "```" in cleaned:
        # Find the content between the first pair of fences.
        parts = cleaned.split("```")
        if len(parts) >= 3:
            cleaned = parts[1].strip()
            # Remove optional language tag.
            if cleaned.startswith(("json\n", "json\r\n")):
                cleaned = cleaned.split("\n", 1)[-1].strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    # Find the FIRST opening brace — skip any inlined tool calls.
    # Try to find the JSON object that starts with known keys.
    idx = -1
    for keyword in ['"product"', '"entries"', '"brief"']:
        pos = cleaned.find(f"{{{keyword}")
        if pos >= 0:
            idx = pos
            break
    if idx < 0:
        idx = cleaned.find("{")
    if idx >= 0:
        cleaned = cleaned[idx:]

    # Progressive parse: try each closing brace from right to left.
    for end in range(len(cleaned), 0, -1):
        if cleaned[end - 1] != "}":
            continue
        candidate = cleaned[:end]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    # Last resort: try the whole cleaned string.
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
        "You are a video editing assistant. You MUST respond with ONLY a "
        "raw JSON object. No explanations, no reasoning, no markdown. "
        "Just the JSON.\n"
    )

    user_prompt = (
        "Create an EditPlan as a JSON object.\n\n"
        "Brief: " + brief.model_dump_json() + "\n\n"
        "Shots:\n" + shots_text + "\n\n"
        "Return ONLY this JSON structure (nothing else):\n"
        '{"entries": [{"shot_id": "source_file#start_time", '
        '"start_trim": 0.0, "end_trim": 10.0, "position": 0, '
        '"text_overlay": null, "transition": null}], '
        '"music_path": null, "total_duration": 30.0}\n\n'
        "JSON:"
    )

    max_retries = 3
    parsed: dict = {}
    for attempt in range(max_retries):
        logger.info("[director-openrouter] Calling %s (attempt %d)...", DEFAULT_GEMINI_MODEL, attempt + 1)
        result = call_openrouter(
            user_prompt,
            system=system_prompt,
            response_schema=None,
            temperature=0.1,
        )
        logger.info("[director-openrouter] Response: %d chars", len(result["text"]))

        try:
            parsed = _repair_json(result["text"])
            if "entries" in parsed:
                break
            logger.warning("[director-openrouter] No 'entries' key in response, retrying...")
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("[director-openrouter] JSON parse failed: %s, retrying...", exc)
            if attempt < max_retries - 1:
                user_prompt = (
                    "Your previous response was not valid JSON. "
                    "You MUST respond with ONLY a raw JSON object.\n\n"
                    + user_prompt
                )
                continue
            raise RuntimeError(
                f"Director failed to produce valid JSON after {max_retries} attempts. "
                f"Last response: {result['text'][:500]}"
            )

    # parsed is already set from the successful attempt above.

    # Validate entries — handle cases where the model returns strings
    # or malformed entries instead of proper dicts.
    raw_entries = parsed.get("entries", [])
    entries: list[EditPlanEntry] = []
    for i, entry_data in enumerate(raw_entries):
        if isinstance(entry_data, str):
            logger.warning(
                "[director-openrouter] entry %d is a string, skipping: %s",
                i, entry_data[:80],
            )
            continue
        if not isinstance(entry_data, dict):
            logger.warning(
                "[director-openrouter] entry %d is not a dict, skipping: %s",
                i, type(entry_data).__name__,
            )
            continue
        try:
            entries.append(EditPlanEntry(**entry_data))
        except Exception as exc:
            logger.warning(
                "[director-openrouter] entry %d invalid: %s",
                i, exc,
            )
            continue

    if not entries:
        # Last resort: generate a simple plan from available shots.
        logger.warning(
            "[director-openrouter] No valid entries from LLM, "
            "generating fallback plan from shots."
        )
        duration = brief.duration_seconds
        per_shot = duration / min(len(index.shots), 5)
        entries = []
        for i, shot in enumerate(index.shots[:5]):
            entries.append(EditPlanEntry(
                shot_id=f"{shot.source_file}#{shot.start_time}",
                start_trim=shot.start_time,
                end_trim=min(shot.end_time, shot.start_time + per_shot),
                position=i,
            ))

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
