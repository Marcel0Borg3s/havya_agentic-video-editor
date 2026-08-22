"""Editor using OpenRouter mode — deterministic FFmpeg execution.

Executes FFmpeg tools directly in Python without LLM involvement.
"""

from __future__ import annotations

import logging
from pathlib import Path

from src.models.schemas import EditPlan, FootageIndex, Shot

logger = logging.getLogger(__name__)


def _merge_ass_files(
    ass_files: list[str],
    entries: list,
    output: str,
    intro_duration: float = 0.0,
) -> str:
    """Merge multiple ASS files with time offsets for sequential clips.

    Args:
        ass_files: List of ASS file paths.
        entries: List of EditPlanEntry objects.
        output: Output ASS file path.
        intro_duration: Duration of intro to add as initial offset.
    """
    from pysubs2 import SSAFile

    merged = SSAFile()
    # Start after intro duration.
    time_offset = intro_duration

    for ass_path, entry in zip(ass_files, entries):
        clip_duration = entry.end_trim - entry.start_trim
        subs = SSAFile.load(ass_path)
        for event in subs.events:
            new_event = event.copy()
            new_event.start += int(time_offset * 1000)
            new_event.end += int(time_offset * 1000)
            merged.events.append(new_event)
        time_offset += clip_duration

    merged.save(output)
    return output


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

    # Debug: log profile status
    if edit_plan.profile is not None:
        logger.info("[editor-openrouter] Profile loaded: %s", edit_plan.profile.name)
        logger.info("[editor-openrouter] Opening: %s", edit_plan.profile.opening)
        logger.info("[editor-openrouter] Closing: %s", edit_plan.profile.closing)
        logger.info("[editor-openrouter] Captions enabled: %s", edit_plan.profile.captions.enabled)
        logger.info("[editor-openrouter] Overlays count: %d", len(edit_plan.profile.overlays))
    else:
        logger.warning("[editor-openrouter] NO PROFILE LOSED!")

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
    rendered = str(working_dir / "rendered.mp4")
    logger.info("[editor-openrouter] Rendering -> %s", rendered)
    from src.tools.render import render_final
    render_final(sequenced, rendered)

    # Step 4: Assemble with opening/closing assets if configured.
    from src.tools.assets import assemble_with_assets
    opening_path = None
    closing_path = None
    intro_duration = 0.0
    if edit_plan.profile is not None:
        if edit_plan.profile.opening is not None:
            opening_path = edit_plan.profile.opening.path
            logger.info("[editor-openrouter] Opening asset: %s", opening_path)
            # Calculate intro duration.
            from src.tools.overlays import get_video_duration
            try:
                intro_duration = get_video_duration(opening_path)
                logger.info("[editor-openrouter] Intro duration: %.1fs", intro_duration)
            except Exception as exc:
                logger.warning("[editor-openrouter] Could not get intro duration: %s", exc)
                intro_duration = 0.0
        if edit_plan.profile.closing is not None:
            closing_path = edit_plan.profile.closing.path
            logger.info("[editor-openrouter] Closing asset: %s", closing_path)

    assembled = str(working_dir / "assembled.mp4")
    if opening_path or closing_path:
        logger.info("[editor-openrouter] Assembling with assets...")
        assemble_with_assets(
            content_video=rendered,
            output=assembled,
            opening_path=opening_path,
            closing_path=closing_path,
            working_dir=str(working_dir / "assets"),
        )
        final_source = assembled
    else:
        final_source = rendered

    # Step 5: Burn captions if enabled in profile.
    captions_enabled = (
        edit_plan.profile is not None
        and edit_plan.profile.captions.enabled
    )
    if captions_enabled:
        logger.info("[editor-openrouter] Generating captions...")
        from src.tools.captions import (
            generate_ass_captions,
            burn_ass_subtitles,
        )

        # Generate ASS for each entry and merge into one file.
        ass_files: list[str] = []
        time_offset = 0.0
        for entry in sorted_entries:
            shot = _resolve_shot(index, entry.shot_id)
            # Use the ACTUAL shot time range for captions, not entry trims
            # which may be wrong from the LLM.
            clip_start = max(entry.start_trim, shot.start_time)
            clip_end = min(entry.end_trim, shot.end_time)
            if clip_end <= clip_start:
                logger.warning(
                    "[editor-openrouter] Skipping captions for entry %d: invalid range [%.1f, %.1f]",
                    entry.position, clip_start, clip_end,
                )
                continue
            ass_out = str(working_dir / f"captions_{entry.position:03d}.ass")
            try:
                generate_ass_captions(
                    footage_index_path=footage_index_path,
                    shot_id=entry.shot_id,
                    clip_start=clip_start,
                    clip_end=clip_end,
                    output=ass_out,
                )
                ass_files.append(ass_out)
                logger.info(
                    "[editor-openrouter] Captions for entry %d: %s",
                    entry.position, ass_out,
                )
            except Exception as exc:
                logger.warning(
                    "[editor-openrouter] Captions failed for entry %d: %s",
                    entry.position, exc,
                )

        # Merge all ASS files with time offsets.
        if ass_files:
            merged_ass = str(working_dir / "captions_merged.ass")
            _merge_ass_files(ass_files, sorted_entries, merged_ass, intro_duration)

            # Burn captions into video.
            captioned = str(working_dir / "captioned.mp4")
            burn_ass_subtitles(final_source, merged_ass, captioned)
            final_source = captioned
            logger.info("[editor-openrouter] Captions burned into video.")

    # Step 6: Apply overlays (title, CTA, credits) if configured.
    has_overlays = (
        edit_plan.profile is not None
        and edit_plan.profile.overlays
    ) or (
        edit_plan.output.title
        or edit_plan.output.channel_name
        or edit_plan.output.credits
    )
    logger.info("[editor-openrouter] has_overlays=%s, profile=%s, overlays=%s, output.title=%s",
                has_overlays,
                edit_plan.profile is not None,
                len(edit_plan.profile.overlays) if edit_plan.profile else 0,
                edit_plan.output.title)
    if has_overlays:
        logger.info("[editor-openrouter] Applying overlays...")
        from src.tools.overlays import apply_plan_overlays

        overlaid = str(working_dir / "overlaid.mp4")
        apply_plan_overlays(
            video=final_source,
            plan=edit_plan,
            output=overlaid,
            working_dir=str(working_dir / "overlays"),
        )
        final_source = overlaid
        logger.info("[editor-openrouter] Overlays applied.")

    # Step 7: Final render to output dir.
    logger.info("[editor-openrouter] Final render -> %s", final_output)
    render_final(final_source, str(final_output))

    if not final_output.exists():
        raise RuntimeError(
            f"Editor completed but final output missing: {final_output}"
        )

    logger.info("[editor-openrouter] Done: %s (%.1f MB)", final_output, final_output.stat().st_size / 1024 / 1024)
    return str(final_output)
