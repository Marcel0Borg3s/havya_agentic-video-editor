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
    if "```" in cleaned:
        parts = cleaned.split("```")
        if len(parts) >= 3:
            cleaned = parts[1].strip()
            if cleaned.startswith(("json\n", "json\r\n")):
                cleaned = cleaned.split("\n", 1)[-1].strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    # Find the FIRST opening brace.
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

    return json.loads(cleaned)


def _shots_to_text(shots: list) -> str:
    """Format shots for the prompt with analysis data."""
    lines: list[str] = []
    for i, shot in enumerate(shots):
        transcript_preview = (shot.transcript[:150] if shot.transcript else "")
        # Build analysis summary.
        analysis_parts = []
        if shot.silence_start > 0.5:
            analysis_parts.append(f"silence_start={shot.silence_start:.1f}s")
        if shot.silence_end > 0.5:
            analysis_parts.append(f"silence_end={shot.silence_end:.1f}s")
        if shot.long_pauses:
            analysis_parts.append(f"long_pauses={len(shot.long_pauses)}")
        if shot.hesitation_count > 0:
            analysis_parts.append(f"hesitations={shot.hesitation_count}")
        if shot.repetition_count > 0:
            analysis_parts.append(f"repetitions={shot.repetition_count}")
        analysis_parts.append(f"speech_ratio={shot.speech_ratio:.2f}")
        analysis_str = ", ".join(analysis_parts)

        lines.append(
            f"Shot {i}:\n"
            f'  source_file: "{shot.source_file}"\n'
            f"  start_time: {shot.start_time}\n"
            f"  end_time: {shot.end_time}\n"
            f'  description: "{shot.description}"\n'
            f"  energy: {shot.energy_level}\n"
            f'  transcript: "{transcript_preview}"\n'
            f"  roll_type: {shot.roll_type}\n"
            f"  analysis: {analysis_str}"
        )
    return "\n".join(lines)


def _validate_and_fix_entries(
    raw_entries: list[dict],
    index: FootageIndex,
    target_duration: float,
) -> list[EditPlanEntry]:
    """Validate LLM entries and fix incorrect trim values.

    The LLM often returns start_trim=0.0 and end_trim=small_value
    instead of the actual shot timestamps. This function detects
    and corrects those mistakes.
    """
    entries: list[EditPlanEntry] = []

    for i, entry_data in enumerate(raw_entries):
        if not isinstance(entry_data, dict):
            logger.warning(
                "[director-openrouter] entry %d is not a dict, skipping", i
            )
            continue

        try:
            shot_id = entry_data.get("shot_id", "")
            if "#" not in shot_id:
                logger.warning(
                    "[director-openrouter] entry %d has invalid shot_id: %s",
                    i, shot_id,
                )
                continue

            # Find the matching shot in the index.
            source_file = shot_id.rsplit("#", 1)[0]
            try:
                declared_start = float(shot_id.rsplit("#", 1)[1])
            except (ValueError, IndexError):
                logger.warning(
                    "[director-openrouter] entry %d has non-numeric start_time in shot_id",
                    i,
                )
                continue

            # Find the actual shot.
            matched_shot = None
            for shot in index.shots:
                if (
                    shot.source_file == source_file
                    and abs(shot.start_time - declared_start) < 0.1
                ):
                    matched_shot = shot
                    break

            if matched_shot is None:
                logger.warning(
                    "[director-openrouter] entry %d shot_id not found in index: %s",
                    i, shot_id,
                )
                continue

            # Get declared trims.
            start_trim = float(entry_data.get("start_trim", matched_shot.start_time))
            end_trim = float(entry_data.get("end_trim", matched_shot.end_time))

            # FIX: If trims are clearly wrong (e.g., start_trim near 0
            # but shot starts at 100s), use the shot's actual range.
            shot_duration = matched_shot.end_time - matched_shot.start_time
            trim_span = end_trim - start_trim

            if (
                start_trim < matched_shot.start_time - 1.0
                or end_trim > matched_shot.end_time + 1.0
                or trim_span < 0.5
                or trim_span > shot_duration + 1.0
            ):
                logger.warning(
                    "[director-openrouter] entry %d has invalid trims [%.1f, %.1f] "
                    "for shot [% .1f, %.1f], clamping to shot range",
                    i, start_trim, end_trim,
                    matched_shot.start_time, matched_shot.end_time,
                )
                start_trim = matched_shot.start_time
                end_trim = matched_shot.end_time

            entries.append(EditPlanEntry(
                shot_id=shot_id,
                start_trim=start_trim,
                end_trim=end_trim,
                position=entry_data.get("position", i),
                text_overlay=entry_data.get("text_overlay"),
                transition=entry_data.get("transition"),
            ))

        except Exception as exc:
            logger.warning(
                "[director-openrouter] entry %d failed validation: %s", i, exc
            )
            continue

    return entries


def _generate_fallback_plan(
    brief: CreativeBrief,
    index: FootageIndex,
) -> list[EditPlanEntry]:
    """Generate a fallback plan when LLM fails or returns bad entries."""
    duration = brief.duration_seconds

    # Prefer A-Roll shots, fallback to unknown, skip pure B-Roll.
    a_roll = [
        s for s in index.shots
        if s.roll_type in ("a-roll", "unknown")
    ]
    candidates = a_roll if a_roll else index.shots

    # Sort by energy_level descending so best shots come first.
    candidates.sort(key=lambda s: s.energy_level, reverse=True)

    # Take up to 5 unique shots, no repeats.
    selected = candidates[: min(len(candidates), 5)]

    per_shot = duration / max(len(selected), 1)
    entries = []
    for i, shot in enumerate(selected):
        entries.append(EditPlanEntry(
            shot_id=f"{shot.source_file}#{shot.start_time}",
            start_trim=shot.start_time,
            end_trim=min(shot.end_time, shot.start_time + per_shot),
            position=i,
        ))

    return entries


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

    # Sort by energy_level descending and take top 5 for the prompt.
    top_shots = sorted(index.shots, key=lambda s: s.energy_level, reverse=True)[:5]
    shots_text = _shots_to_text(top_shots)

    system_prompt = (
        "You are a video editing assistant. "
        "You MUST respond with ONLY a raw JSON object. "
        "No explanations, no reasoning, no markdown. Just the JSON."
    )

    user_prompt = (
        "Create an EditPlan as a JSON object.\n\n"
        "## Brief\n"
        + brief.model_dump_json() + "\n\n"
        "## Available shots\n"
        + shots_text + "\n\n"
        "## CRITICAL RULES FOR TRIM VALUES\n"
        "Each shot has start_time and end_time in SECONDS from the "
        "beginning of the source video.\n"
        "- start_trim MUST be >= shot's start_time\n"
        "- end_trim MUST be <= shot's end_time\n"
        "- end_trim MUST be > start_trim\n"
        "- Do NOT use 0.0 as start_trim unless the shot actually starts at 0.0\n"
        "- Do NOT use relative offsets. Use the ABSOLUTE timestamps from the shot.\n\n"
        "## EDITORIAL ANALYSIS\n"
        "Each shot includes analysis data:\n"
        "- silence_start/silence_end: seconds of silence at shot boundaries\n"
        "- long_pauses: count of pauses > 0.8s between words\n"
        "- hesitations: count of filler words (um, uh, é, tipo, etc.)\n"
        "- repetitions: count of repeated words\n"
        "- speech_ratio: fraction of shot duration with speech (0.0-1.0)\n\n"
        "Use this to improve edit quality:\n"
        "- Trim silence from start/end of shots\n"
        "- Remove or reduce sections with many hesitations\n"
        "- Avoid shots with low speech_ratio (< 0.3)\n"
        "- Prefer shots with fewer repetitions\n\n"
        f"## Target duration: {brief.duration_seconds} seconds\n\n"
        "## Example (WRONG - do NOT do this):\n"
        '{"entries": [{"shot_id": "video.mp4#102.5", "start_trim": 0.0, '
        '"end_trim": 10.0, "position": 0}]} '
        "// WRONG: start_trim should be ~102.5, not 0.0\n\n"
        "## Example (CORRECT):\n"
        '{"entries": [{"shot_id": "video.mp4#102.5", "start_trim": 102.5, '
        '"end_trim": 115.0, "position": 0}]} '
        "// CORRECT: uses actual shot timestamps\n\n"
        "Return ONLY this JSON structure:\n"
        '{"entries": [{"shot_id": "source_file#start_time", '
        '"start_trim": <ACTUAL_SHOT_START_TIME>, '
        '"end_trim": <ACTUAL_SHOT_END_TIME>, "position": 0, '
        '"text_overlay": null, "transition": null}], '
        '"music_path": null, "total_duration": <TARGET_SECONDS>}\n\n'
        "JSON:"
    )

    max_retries = 3
    parsed: dict = {}
    for attempt in range(max_retries):
        logger.info("[director-openrouter] Calling %s (attempt %d)...", DEFAULT_GEMINI_MODEL, attempt + 1)
        _debug_log_prompt(system_prompt, user_prompt)
        result = call_openrouter(
            user_prompt,
            system=system_prompt,
            response_schema=None,
            temperature=0.1,
        )
        logger.info(
            "[director-openrouter] Response: %d chars", len(result["text"])
        )

        try:
            parsed = _repair_json(result["text"])
            if "entries" in parsed:
                break
            logger.warning(
                "[director-openrouter] No 'entries' key in response, retrying..."
            )
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning(
                "[director-openrouter] JSON parse failed: %s, retrying...", exc
            )
            if attempt < max_retries - 1:
                user_prompt = (
                    "Your previous response was NOT valid JSON. "
                    "You MUST respond with ONLY a raw JSON object matching "
                    "the EditPlan schema. No explanations, no markdown.\n\n"
                    + user_prompt
                )
                continue
            raise RuntimeError(
                f"Director failed to produce valid JSON after {max_retries} attempts. "
                f"Last response: {result['text'][:500]}"
            )

    # Validate and fix entries from LLM response.
    raw_entries = parsed.get("entries", [])
    entries = _validate_and_fix_entries(raw_entries, index, brief.duration_seconds)

    # If no valid entries, use fallback.
    if not entries:
        logger.warning(
            "[director-openrouter] No valid entries from LLM, "
            "generating fallback plan from shots."
        )
        entries = _generate_fallback_plan(brief, index)

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
        len(entries), total_duration,
    )
    return edit_plan


def _debug_log_prompt(system: str, user: str) -> None:
    """Log prompt details for debugging."""
    logger.info("[director-openrouter] System prompt: %d chars", len(system))
    logger.info("[director-openrouter] User prompt: %d chars", len(user))
    logger.info("[director-openrouter] Total prompt: %d chars (~%d tokens)",
                len(system) + len(user), (len(system) + len(user)) // 4)
