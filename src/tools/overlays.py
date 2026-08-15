"""Deterministic text-overlay orchestration for rendered videos."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Literal, cast

from src.models.schemas import EditPlan, OverlayOptions
from src.tools.edit import add_text_overlay


def get_video_duration(video: str) -> float:
    """Return video duration in seconds using ffprobe."""
    if not Path(video).exists():
        raise FileNotFoundError(f"Video not found: {video}")
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        video,
    ]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("ffprobe is required to apply timed overlays") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"ffprobe failed: {exc.stderr}") from exc
    try:
        return max(0.0, float(result.stdout.strip()))
    except ValueError as exc:
        raise RuntimeError(f"ffprobe returned invalid duration: {result.stdout!r}") from exc


def _position_for_ffmpeg(position: str) -> str:
    """Map profile positions to the existing drawtext presets."""
    if position == "bottom":
        return "bottom-third"
    if position in {"top", "center", "bottom-third"}:
        return position
    raise ValueError(f"unsupported overlay position: {position!r}")


def build_plan_overlays(plan: EditPlan, duration: float) -> list[OverlayOptions]:
    """Build explicit plus metadata-derived overlays for a plan."""
    overlays: list[OverlayOptions] = []
    if plan.profile is not None:
        overlays.extend(plan.profile.overlays)

    output = plan.output
    if output.title:
        overlays.append(
            OverlayOptions(role="title",
                text=output.title,
                start=0,
                duration=min(5.0, duration),
                position="top")
        )
    if output.channel_name:
        overlays.append(
            OverlayOptions(
                role="subscribe",
                text=f"Inscreva-se em {output.channel_name}",
                start=max(0.0, duration - 8),
                duration=min(6.0, duration),
                position="bottom",
            )
        )
    if output.credits:
        overlays.append(
            OverlayOptions(
                role="credits",
                text=output.credits,
                start=max(0.0, duration - 5),
                duration=min(5.0, duration),
                position="center",
            )
        )
    return overlays


def apply_plan_overlays(
    video: str,
    plan: EditPlan,
    output: str,
    *,
    working_dir: str,
) -> str:
    """Apply all configured text overlays and return the final output path."""
    has_profile_overlays = bool(plan.profile and plan.profile.overlays)
    has_output_overlays = bool(
        plan.output.title or plan.output.channel_name or plan.output.credits
    )
    if not has_profile_overlays and not has_output_overlays:
        return video

    overlays = build_plan_overlays(plan, get_video_duration(video))
    if not overlays:
        return video

    work = Path(working_dir)
    work.mkdir(parents=True, exist_ok=True)
    current = video
    for index, overlay in enumerate(overlays):
        is_last = index == len(overlays) - 1
        next_path = Path(output) if is_last else work / f"overlay_{index:02d}.mp4"
        add_text_overlay(
            video=current,
            text=overlay.text,
            position=cast(
                Literal["bottom-third", "center", "top"],
                _position_for_ffmpeg(overlay.position),
            ),
            start=overlay.start,
            duration=overlay.duration,
            output=str(next_path),
        )
        current = str(next_path)
    return current


__all__ = ["apply_plan_overlays", "build_plan_overlays", "get_video_duration"]
