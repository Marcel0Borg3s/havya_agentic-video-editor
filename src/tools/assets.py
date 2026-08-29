"""Media-asset normalization and assembly helpers."""

from __future__ import annotations

from pathlib import Path
from src.tools.edit import sequence_clips, sequence_clips_with_crossfade
from src.tools.render import render_final


def normalize_asset(asset_path: str, output: str, resolution: str = "1080x1920") -> str:
    """Normalize an external asset to the editor's delivery format."""
    if not Path(asset_path).exists():
        raise FileNotFoundError(f"Media asset not found: {asset_path}")
    return render_final(asset_path, output, resolution=resolution)


def assemble_with_assets(
    content_video: str,
    output: str,
    *,
    opening_path: str | None = None,
    closing_path: str | None = None,
    working_dir: str = "output/working/assets",
    resolution: str | None = None,
    crossfade_duration: float = 0.5,
) -> str:
    """Assemble optional opening/content/closing videos into one MP4.

    External assets are normalized before concatenation so resolution,
    pixel aspect ratio, codec, and audio encoding match the rendered content.
    Uses crossfade transitions between clips for smooth playback.

    Args:
        content_video: Path to the main edited content.
        output: Destination path for the assembled video.
        opening_path: Optional path to an opening/intro video.
        closing_path: Optional path to a closing/outro video.
        working_dir: Directory for intermediate normalized files.
        resolution: Target resolution. If None, detects from content_video.
        crossfade_duration: Duration of crossfade transitions in seconds.
    """
    if not Path(content_video).exists():
        raise FileNotFoundError(f"Content video not found: {content_video}")
    if opening_path is None and closing_path is None:
        return content_video

    # Auto-detect resolution from content video if not specified.
    if resolution is None:
        import subprocess as _sp
        import json as _json
        probe = _sp.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_streams", "-select_streams", "v:0", content_video],
            capture_output=True, text=True,
        )
        streams = _json.loads(probe.stdout).get("streams", [{}])
        if streams:
            w = streams[0].get("width", 1920)
            h = streams[0].get("height", 1080)
        else:
            w, h = 1920, 1080
        resolution = f"{w}x{h}"

    work = Path(working_dir)
    work.mkdir(parents=True, exist_ok=True)
    clips: list[str] = []

    if opening_path is not None:
        opening_normalized = work / "opening_normalized.mp4"
        normalize_asset(opening_path, str(opening_normalized), resolution)
        clips.append(str(opening_normalized))

    clips.append(content_video)

    if closing_path is not None:
        closing_normalized = work / "closing_normalized.mp4"
        normalize_asset(closing_path, str(closing_normalized), resolution)
        clips.append(str(closing_normalized))

    # Use crossfade for smooth transitions between clips.
    if len(clips) > 1 and crossfade_duration > 0:
        return sequence_clips_with_crossfade(clips, output, crossfade_duration)
    else:
        return sequence_clips(clips, output)


__all__ = ["assemble_with_assets", "normalize_asset"]

if __name__ == "__main__":
    raise SystemExit("Use normalize_asset() or assemble_with_assets() from Python.")
