"""Editor using OpenRouter mode — deterministic FFmpeg execution.

Executes FFmpeg tools directly in Python without LLM involvement.
"""

from __future__ import annotations

import logging
from pathlib import Path

from src.models.schemas import EditPlan, FootageIndex, Shot

logger = logging.getLogger(__name__)


def _resolve_shot(footage_index: FootageIndex, shot_id: str) -> Shot:
    if "#" not in shot_id:
        raise ValueError(f"Invalid shot_id format: {shot_id!r}")
    source_file = shot_id.rsplit("#", 1)[0]
    start_time = float(shot_id.rsplit("#", 1)[1])
    for shot in footage_index.shots:
        if shot.source_file == source_file and abs(shot.start_time - start_time) < 0.01:
            return shot
    raise ValueError(f"Shot not found: {shot_id!r}")


def run_editor_openrouter(
    edit_plan: EditPlan,
    footage_index_path: str,
    output_dir: str = "output",
) -> str:
    """Execute the EditPlan using FFmpeg tools directly (no LLM)."""
    from src.tools.edit import cut_clip, sequence_clips

    index_path = Path(footage_index_path)
    if not index_path.exists():
        raise FileNotFoundError(f"footage_index_path not found: {footage_index_path}")

    index = FootageIndex.model_validate_json(index_path.read_text())

    brief_slug = edit_plan.brief.product.lower().replace(" ", "_")[:30]
    working_dir = Path(output_dir) / "working" / brief_slug
    final_dir = Path(output_dir) / "final"
    working_dir.mkdir(parents=True, exist_ok=True)
    final_dir.mkdir(parents=True, exist_ok=True)

    final_output = final_dir / f"{brief_slug}.mp4"
    if final_output.exists():
        final_output.unlink()

    logger.info("[editor-openrouter] Processing %d entries...", len(edit_plan.entries))

    # Step 1: Clip each entry.
    clip_paths: list[str] = []
    sorted_entries = sorted(edit_plan.entries, key=lambda e: e.position)
    for entry in sorted_entries:
        shot = _resolve_shot(index, entry.shot_id)
        clip_out = str(working_dir / f"clip_{entry.position:03d}.mp4")
        logger.info(
            "[editor-openrouter] Clipping %s [%.1f-%.1f] -> %s",
            entry.shot_id, entry.start_trim, entry.end_trim, clip_out,
        )
        cut_clip(shot.source_file, entry.start_trim, entry.end_trim, clip_out)
        clip_paths.append(clip_out)

    # Step 2: Sequence all clips.
    sequenced = str(working_dir / "sequenced.mp4")
    logger.info("[editor-openrouter] Sequencing %d clips...", len(clip_paths))
    sequence_clips(clip_paths, sequenced)

    # Step 3: Re-encode for delivery.
    logger.info("[editor-openrouter] Rendering final -> %s", final_output)
    from src.tools.render import render_final
    render_final(sequenced, str(final_output))

    if not final_output.exists():
        raise RuntimeError(
            f"Editor completed but final output missing: {final_output}"
        )

    logger.info("[editor-openrouter] Done: %s (%.1f MB)", final_output, final_output.stat().st_size / 1024 / 1024)
    return str(final_output)
