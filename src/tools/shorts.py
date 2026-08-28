"""Shorts generator: creates vertical 9:16 clips from main video."""

from __future__ import annotations

import logging
from pathlib import Path

from src.models.schemas import EditPlan, FootageIndex, Shot, ShortsOptions

logger = logging.getLogger(__name__)


def select_short_segments(
    shots: list[Shot],
    shorts_options: ShortsOptions,
    total_duration: float,
) -> list[dict]:
    """Select high-potential segments for Shorts.

    Returns list of {shot_id, start, end, score} dicts.
    """
    count = shorts_options.count
    max_dur = shorts_options.duration_seconds

    # Score shots by energy and speech ratio.
    scored: list[dict] = []
    for shot in shots:
        score = shot.energy_level * 0.6 + shot.speech_ratio * 0.4
        if shot.hesitation_count > 2:
            score *= 0.5
        if shot.repetition_count > 2:
            score *= 0.5
        duration = shot.end_time - shot.start_time
        if duration < 3.0:
            continue
        scored.append({
            "shot_id": f"{shot.source_file}#{shot.start_time}",
            "start": shot.start_time,
            "end": shot.end_time,
            "score": score,
            "duration": duration,
        })

    scored.sort(key=lambda s: s["score"], reverse=True)

    # Select top segments, fitting within max_dur each.
    selected: list[dict] = []
    for s in scored:
        if len(selected) >= count:
            break
        dur = min(s["duration"], max_dur)
        selected.append({
            "shot_id": s["shot_id"],
            "start": s["start"],
            "end": s["start"] + dur,
            "score": s["score"],
        })

    return selected


def render_short(
    source_video: str,
    start: float,
    end: float,
    output: str,
    cta_text: str | None = None,
) -> str:
    """Render a single Short clip in 9:16 format.

    Crops to center and scales to 1080x1920.
    """
    import subprocess

    duration = end - start
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", source_video,
        "-t", str(duration),
        "-vf", (
            "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,"
            "scale=1080:1920:force_original_aspect_ratio=decrease,"
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,"
            "setsar=1"
        ),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        output,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return output


def generate_shorts(
    main_video: str,
    edit_plan: EditPlan,
    footage_index_path: str,
    output_dir: str,
) -> list[str]:
    """Generate multiple Shorts from the main video.

    Returns list of generated Short file paths.
    """
    from src.models.schemas import FootageIndex

    if not edit_plan.profile or not edit_plan.profile.shorts.enabled:
        logger.info("[shorts] Shorts not enabled in profile")
        return []

    shorts_opts = edit_plan.profile.shorts
    index = FootageIndex.model_validate_json(
        Path(footage_index_path).read_text("utf-8")
    )

    # Get total video duration.
    from src.tools.overlays import get_video_duration
    total_dur = get_video_duration(main_video)

    # Select segments.
    segments = select_short_segments(index.shots, shorts_opts, total_dur)
    if not segments:
        logger.warning("[shorts] No suitable segments found")
        return []

    logger.info("[shorts] Generating %d shorts from %d segments", len(segments), len(segments))

    out_dir = Path(output_dir) / "shorts"
    out_dir.mkdir(parents=True, exist_ok=True)

    generated: list[str] = []
    for i, seg in enumerate(segments):
        out_path = str(out_dir / f"short_{i+1:02d}.mp4")
        logger.info("[shorts] Short %d: %.1fs-%.1fs -> %s", i+1, seg["start"], seg["end"], out_path)
        try:
            render_short(
                source_video=main_video,
                start=seg["start"],
                end=seg["end"],
                output=out_path,
            )
            generated.append(out_path)
        except Exception as exc:
            logger.warning("[shorts] Failed to render short %d: %s", i+1, exc)

    logger.info("[shorts] Generated %d/%d shorts", len(generated), len(segments))
    return generated
