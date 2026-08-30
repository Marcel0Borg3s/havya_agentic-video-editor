"""Refine module: splits shots at pause boundaries to remove dead air.

Takes an EditPlan from the Director and refines it by:
1. Analyzing word timestamps within each entry
2. Detecting gaps > threshold between words
3. Splitting entries at pause boundaries
4. Removing silent segments
"""

from __future__ import annotations

import logging
from pathlib import Path

from src.models.schemas import EditPlan, EditPlanEntry, FootageIndex, Shot

logger = logging.getLogger(__name__)

# Minimum gap (seconds) to consider a pause.
PAUSE_THRESHOLD = 0.5

# Minimum clip duration after removing pauses.
MIN_CLIP_DURATION = 0.3


def _find_pauses_in_shot(
    shot: Shot,
    clip_start: float,
    clip_end: float,
    threshold: float = PAUSE_THRESHOLD,
) -> list[tuple[float, float]]:
    """Find pauses (gaps between words) within a clip range.

    Returns list of (pause_start, pause_end) tuples.
    """
    pauses: list[tuple[float, float]] = []

    # Get words within the clip range.
    words_in_clip = [
        w for w in shot.words
        if w.start >= clip_start and w.end <= clip_end
    ]

    if len(words_in_clip) < 2:
        return pauses

    # Find gaps between consecutive words.
    for i in range(len(words_in_clip) - 1):
        gap_start = words_in_clip[i].end
        gap_end = words_in_clip[i + 1].start
        gap_duration = gap_end - gap_start

        if gap_duration >= threshold:
            pauses.append((gap_start, gap_end))

    return pauses


def _split_clip_at_pauses(
    clip_start: float,
    clip_end: float,
    pauses: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    """Split a clip range at pause boundaries, removing pause segments.

    Returns list of (start, end) tuples for non-pause segments.
    """
    if not pauses:
        return [(clip_start, clip_end)]

    segments: list[tuple[float, float]] = []
    current_start = clip_start

    for pause_start, pause_end in pauses:
        # Add segment before pause (if valid).
        if pause_start - current_start >= MIN_CLIP_DURATION:
            segments.append((current_start, pause_start))
        current_start = pause_end

    # Add final segment after last pause.
    if clip_end - current_start >= MIN_CLIP_DURATION:
        segments.append((current_start, clip_end))

    return segments


def refine_edit_plan(
    edit_plan: EditPlan,
    footage_index_path: str,
    pause_threshold: float = PAUSE_THRESHOLD,
) -> EditPlan:
    """Refine an EditPlan by splitting entries at pause boundaries.

    Analyzes word timestamps within each entry and splits at gaps
    greater than the threshold, effectively removing dead air.
    """
    if not Path(footage_index_path).exists():
        logger.warning("[refine] Footage index not found, skipping refinement")
        return edit_plan

    index = FootageIndex.model_validate_json(
        Path(footage_index_path).read_text("utf-8")
    )

    refined_entries: list[EditPlanEntry] = []
    position = 0

    for entry in edit_plan.entries:
        # Find the matching shot.
        shot = None
        source_file = entry.shot_id.rsplit("#", 1)[0]
        try:
            declared_start = float(entry.shot_id.rsplit("#", 1)[1])
        except (ValueError, IndexError):
            continue

        for s in index.shots:
            if s.source_file == source_file and abs(s.start_time - declared_start) < 0.1:
                shot = s
                break

        if shot is None:
            logger.warning("[refine] Shot not found: %s, keeping original", entry.shot_id)
            refined_entries.append(EditPlanEntry(
                shot_id=entry.shot_id,
                start_trim=entry.start_trim,
                end_trim=entry.end_trim,
                position=position,
                text_overlay=entry.text_overlay,
                transition=entry.transition,
            ))
            position += 1
            continue

        # Find pauses within this entry's range.
        pauses = _find_pauses_in_shot(shot, entry.start_trim, entry.end_trim, pause_threshold)

        if not pauses:
            # No pauses found, keep original entry.
            refined_entries.append(EditPlanEntry(
                shot_id=entry.shot_id,
                start_trim=entry.start_trim,
                end_trim=entry.end_trim,
                position=position,
                text_overlay=entry.text_overlay,
                transition=entry.transition,
            ))
            position += 1
        else:
            # Split at pause boundaries.
            segments = _split_clip_at_pauses(entry.start_trim, entry.end_trim, pauses)
            logger.info(
                "[refine] Shot %s: found %d pauses, split into %d segments",
                entry.shot_id, len(pauses), len(segments),
            )

            for seg_start, seg_end in segments:
                refined_entries.append(EditPlanEntry(
                    shot_id=entry.shot_id,
                    start_trim=seg_start,
                    end_trim=seg_end,
                    position=position,
                    text_overlay=None,  # Don't duplicate overlays
                    transition="cut",
                ))
                position += 1

    # Create refined plan.
    refined = edit_plan.model_copy(update={"entries": refined_entries})

    logger.info(
        "[refine] Refined plan: %d entries (was %d)",
        len(refined_entries), len(edit_plan.entries),
    )

    return refined
