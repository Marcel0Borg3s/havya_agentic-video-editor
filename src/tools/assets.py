"""Media-asset normalization and assembly helpers."""

from __future__ import annotations

from pathlib import Path

from src.tools.edit import sequence_clips
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
    resolution: str = "1080x1920",
) -> str:
    """Assemble optional opening/content/closing videos into one MP4.

    External assets are normalized before concatenation so resolution,
    pixel aspect ratio, codec, and audio encoding match the rendered content.
    The content video is not normalized again because it has already passed
    through the Editor's final render step.
    """
    if not Path(content_video).exists():
        raise FileNotFoundError(f"Content video not found: {content_video}")
    if opening_path is None and closing_path is None:
        return content_video

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

    return sequence_clips(clips, output)


__all__ = ["assemble_with_assets", "normalize_asset"]


if __name__ == "__main__":
    raise SystemExit("Use normalize_asset() or assemble_with_assets() from Python.")

