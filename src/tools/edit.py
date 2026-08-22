"""FFmpeg editing tools for the Editor agent.

Each function shells out to ``ffmpeg`` via ``subprocess.run`` with a list
of arguments (never ``shell=True``) so that user-supplied paths and text
cannot inject commands. Functions raise ``RuntimeError`` with the captured
``ffmpeg`` stderr on failure to make debugging straightforward.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Literal  # noqa: F401 — used in deferred annotations

DEFAULT_FONT = "/System/Library/Fonts/Helvetica.ttc"

# Map friendly position names to FFmpeg drawtext x/y expressions.
# y values are computed in terms of frame height (h) and text height (text_h).
_POSITION_PRESETS: dict[str, tuple[str, str]] = {
    "bottom-third": ("(w-text_w)/2", "h-(h/3)-(text_h/2)"),
    "center": ("(w-text_w)/2", "(h-text_h)/2"),
    "top": ("(w-text_w)/2", "h/12"),
}


def _ensure_parent(output: str) -> None:
    """Create the parent directory for ``output`` if missing."""
    Path(output).parent.mkdir(parents=True, exist_ok=True)


def _require_file(path: str, kind: str) -> None:
    """Raise ``FileNotFoundError`` if ``path`` does not exist on disk."""
    if not Path(path).exists():
        raise FileNotFoundError(f"{kind} not found: {path}")


def _run_ffmpeg(cmd: list[str]) -> None:
    """Invoke ffmpeg with ``check=True``; re-raise stderr as ``RuntimeError``.

    Args:
        cmd: Full argv list beginning with ``ffmpeg``.

    Raises:
        RuntimeError: If ffmpeg exits with a non-zero status.
    """
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg failed: {e.stderr}") from e


def _escape_drawtext(text: str) -> str:
    """Escape characters that are special inside an FFmpeg drawtext value.

    drawtext uses ``:`` to separate options and ``'`` to quote the value, and
    treats backslashes as escapes. Escape order matters — backslash first.
    """
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
    )


def cut_clip(source: str, start: float, end: float, output: str) -> str:
    """Extract a sub-clip from ``source`` between ``start`` and ``end`` seconds.

    Uses FFmpeg stream copy (``-c copy``) for millisecond-fast extraction
    without re-encoding. The cut may snap to the nearest keyframe because
    stream copy cannot split frames mid-GOP.

    Args:
        source: Path to the source video file.
        start: Start time in seconds.
        end: End time in seconds (must be greater than ``start``).
        output: Destination path for the extracted clip.

    Returns:
        The ``output`` path on success.

    Raises:
        FileNotFoundError: If ``source`` does not exist.
        ValueError: If ``end`` is not greater than ``start``.
        RuntimeError: If ffmpeg fails.
    """
    _require_file(source, "Source video")
    if end <= start:
        raise ValueError(f"end ({end}) must be greater than start ({start})")
    _ensure_parent(output)

    duration = end - start
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{start}",
        "-i",
        source,
        "-t",
        f"{duration}",
        "-c",
        "copy",
        output,
    ]
    _run_ffmpeg(cmd)
    return output


def sequence_clips(clips: list[str], output: str) -> str:
    """Concatenate ``clips`` in order using FFmpeg concat filter.

    Handles clips with or without audio streams by detecting each
    input's streams and generating silent audio where needed.

    Args:
        clips: Ordered list of clip paths to concatenate.
        output: Destination path for the joined video.

    Returns:
        The ``output`` path on success.

    Raises:
        ValueError: If ``clips`` is empty.
        FileNotFoundError: If any clip is missing.
        RuntimeError: If ffmpeg fails.
    """
    if not clips:
        raise ValueError("clips list must not be empty")
    for clip in clips:
        _require_file(clip, "Clip")
    _ensure_parent(output)

    import json as _json
    import subprocess as _sp

    # Detect streams and durations for each input.
    clip_info: list[dict] = []
    for clip in clips:
        probe = _sp.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_streams", "-show_entries", "format=duration", clip],
            capture_output=True, text=True,
        )
        data = _json.loads(probe.stdout)
        streams = data.get("streams", [])
        duration = float(data.get("format", {}).get("duration", "1"))
        has_audio = any(s.get("codec_type") == "audio" for s in streams)
        clip_info.append({"has_audio": has_audio, "duration": duration})

    # Build filter graph.
    inputs: list[str] = []
    filter_parts: list[str] = []
    v_refs: list[str] = []
    a_refs: list[str] = []

    for i, clip in enumerate(clips):
        inputs.extend(["-i", clip])
        v_refs.append(f"[{i}:v:0]")

        if clip_info[i]["has_audio"]:
            a_refs.append(f"[{i}:a:0]")
        else:
            # Generate silent audio matching this clip's duration.
            dur = clip_info[i]["duration"]
            filter_parts.append(
                f"aevalsrc=0:d={dur}:s=44100:c=mono[sil{i}]"
            )
            a_refs.append(f"[sil{i}]")

    # Concat video.
    n = len(clips)
    filter_parts.append(
        f"{''.join(v_refs)}concat=n={n}:v=1:a=0[vout]"
    )

    # Concat audio (all inputs now have audio — real or silent).
    filter_parts.append(
        f"{''.join(a_refs)}concat=n={n}:v=0:a=1[aout]"
    )

    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        output,
    ]
    _run_ffmpeg(cmd)
    return output


def sequence_clips_with_crossfade(
    clips: list[str],
    output: str,
    crossfade_duration: float = 0.5,
) -> str:
    """Concatenate clips with crossfade transitions between them.

    Uses FFmpeg xfade (video) and acrossfade (audio) filters to
    create smooth transitions between clips.

    Args:
        clips: Ordered list of clip paths.
        output: Destination path.
        crossfade_duration: Duration of crossfade in seconds.

    Returns:
        The output path.
    """
    if not clips:
        raise ValueError("clips list must not be empty")
    for clip in clips:
        _require_file(clip, "Clip")
    _ensure_parent(output)

    import json as _json
    import subprocess as _sp

    if len(clips) == 1:
        # Single clip, just copy.
        cmd = ["ffmpeg", "-y", "-i", clips[0], "-c", "copy", output]
        _run_ffmpeg(cmd)
        return output

    # Detect streams and durations.
    clip_info: list[dict] = []
    for clip in clips:
        probe = _sp.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_streams", "-show_entries", "format=duration", clip],
            capture_output=True, text=True,
        )
        data = _json.loads(probe.stdout)
        streams = data.get("streams", [])
        duration = float(data.get("format", {}).get("duration", "1"))
        has_audio = any(s.get("codec_type") == "audio" for s in streams)
        clip_info.append({"has_audio": has_audio, "duration": duration})

    # Build inputs.
    inputs: list[str] = []
    for clip in clips:
        inputs.extend(["-i", clip])

    n = len(clips)
    filter_parts: list[str] = []

    # Build xfade chain for video.
    # Each xfade takes two inputs and produces one output.
    # The offset is the cumulative duration minus crossfade.
    prev_label = "[0:v]"
    for i in range(1, n):
        offset = sum(c["duration"] for c in clip_info[:i]) - (i * crossfade_duration)
        offset = max(0.0, offset)
        out_label = f"[vxfade{i}]"
        filter_parts.append(
            f"{prev_label}[{i}:v]xfade=transition=fade"
            f":duration={crossfade_duration}:offset={offset:.3f}{out_label}"
        )
        prev_label = out_label
    filter_parts.append(f"{prev_label}[vout]")

    # Build acrossfade chain for audio.
    prev_label = "[0:a]"
    for i in range(1, n):
        out_label = f"[axfade{i}]"
        filter_parts.append(
            f"{prev_label}[{i}:a]acrossfade=d={crossfade_duration}:c1=tri:c2=tri{out_label}"
        )
        prev_label = out_label
    filter_parts.append(f"{prev_label}[aout]")

    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        output,
    ]
    _run_ffmpeg(cmd)
    return output


def add_text_overlay(
    video: str,
    text: str,
    position: Literal["bottom-third", "center", "top"],
    start: float,
    duration: float,
    output: str,
) -> str:
    """Burn a text overlay onto ``video`` for a timed window.

    Uses the FFmpeg ``drawtext`` filter with one of three positional presets
    (``bottom-third``, ``center``, ``top``). Visibility is controlled by
    ``enable='between(t,start,start+duration)'``. Special characters in the
    text are escaped because ``drawtext`` is finicky about ``:``, ``'``,
    ``\\``, and ``%``.

    Args:
        video: Input video path.
        text: Overlay text to draw.
        position: One of ``bottom-third``, ``center``, ``top``.
        start: Time in seconds when the overlay appears.
        duration: How long (in seconds) the overlay stays on screen.
        output: Destination path for the rendered video.

    Returns:
        The ``output`` path on success.

    Raises:
        FileNotFoundError: If ``video`` is missing.
        ValueError: If ``position`` is not a known preset or ``duration`` is
            not positive.
        RuntimeError: If ffmpeg fails.
    """
    _require_file(video, "Video")
    if position not in _POSITION_PRESETS:
        raise ValueError(
            f"unknown position '{position}'; expected one of "
            f"{sorted(_POSITION_PRESETS)}"
        )
    if duration <= 0:
        raise ValueError(f"duration must be positive, got {duration}")
    _ensure_parent(output)

    x_expr, y_expr = _POSITION_PRESETS[position]
    end = start + duration

    # Write text to a temp file to avoid FFmpeg drawtext quoting issues
    # with apostrophes, colons, and other special characters in subtitles.
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        prefix="drawtext_",
        delete=False,
        encoding="utf-8",
    )
    text_file_path = tmp.name
    try:
        tmp.write(text)
        tmp.close()

        drawtext = (
            f"drawtext=fontfile='{DEFAULT_FONT}'"
            f":textfile='{text_file_path}'"
            f":fontcolor=white"
            f":fontsize=40"
            f":borderw=2"
            f":bordercolor=black@0.85"
            f":x={x_expr}"
            f":y={y_expr}"
            f":enable='between(t,{start},{end})'"
        )

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            video,
            "-vf",
            drawtext,
            "-c:a",
            "copy",
            output,
        ]
        _run_ffmpeg(cmd)
    finally:
        try:
            os.unlink(text_file_path)
        except OSError:
            pass
    return output


def composite_broll(
    base_video: str,
    overlays: list[dict],
    output: str,
) -> str:
    """Overlay B-Roll video segments onto a base A-Roll video.

    Takes a base video (sequenced A-Roll with continuous narration audio)
    and composites B-Roll clips on top at specified timestamps, keeping
    the base audio playing through. Each overlay dict has:
      - ``path``: path to the normalized B-Roll clip
      - ``start``: timeline position (seconds) where the overlay begins
      - ``duration``: how long the overlay shows (seconds)

    Uses FFmpeg's overlay filter with ``enable='between(t,start,end)'``
    and ``-map 0:a`` to preserve the base audio untouched.

    Args:
        base_video: Path to the base A-Roll sequenced video.
        overlays: List of dicts, each with ``path``, ``start``, ``duration``.
        output: Destination path for the composited video.

    Returns:
        The ``output`` path on success.

    Raises:
        FileNotFoundError: If ``base_video`` or any overlay path is missing.
        ValueError: If ``overlays`` is empty.
        RuntimeError: If ffmpeg fails.
    """
    _require_file(base_video, "Base video")
    if not overlays:
        raise ValueError("overlays list must not be empty")
    for ov in overlays:
        _require_file(ov["path"], "Overlay clip")
    _ensure_parent(output)

    # Build FFmpeg command:
    # -i base_video -i broll1.mp4 -i broll2.mp4 ...
    # filter_complex: scale each overlay to match base, then chain overlays
    inputs = ["-i", base_video]
    for ov in overlays:
        inputs.extend(["-i", ov["path"]])

    filter_parts: list[str] = []
    prev_label = "0:v"

    for idx, ov in enumerate(overlays):
        input_idx = idx + 1  # 0 is base video
        start = ov["start"]
        end = start + ov["duration"]
        scaled_label = f"s{idx}"
        out_label = f"v{idx}"

        # Scale overlay to match base resolution and shift PTS so the
        # B-Roll frames arrive at the correct timeline position.  Without
        # the +{start}/TB term the clip starts at PTS 0, FFmpeg consumes
        # all its frames before the enable window opens, and the viewer
        # sees a frozen last-frame instead of a playing clip.
        filter_parts.append(
            f"[{input_idx}:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
            f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,"
            f"setpts=PTS-STARTPTS+{start}/TB[{scaled_label}]"
        )
        # Overlay on previous stage.  eof_action=pass lets the base video
        # show through once the B-Roll clip runs out of frames.
        filter_parts.append(
            f"[{prev_label}][{scaled_label}]overlay=0:0:"
            f"eof_action=pass:"
            f"enable='between(t,{start:.3f},{end:.3f})'[{out_label}]"
        )
        prev_label = out_label

    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg",
        "-y",
        *inputs,
        "-filter_complex",
        filter_complex,
        "-map",
        f"[{prev_label}]",
        "-map",
        "0:a",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-c:a",
        "copy",
        output,
    ]
    _run_ffmpeg(cmd)
    return output


def add_music(video: str, music: str, volume: float, output: str) -> str:
    """Mix ``music`` under ``video``'s original audio at ``volume`` scale.

    The music track is scaled by ``volume`` and then ``amix``'d with the
    video's existing audio. ``duration=first`` keeps the output the same
    length as the video, dropping or padding the music as needed.

    Args:
        video: Input video path (must contain an audio stream).
        music: Music track path.
        volume: Linear gain applied to the music track only (e.g. ``0.3``
            for 30% volume).
        output: Destination path for the mixed video.

    Returns:
        The ``output`` path on success.

    Raises:
        FileNotFoundError: If ``video`` or ``music`` is missing.
        ValueError: If ``volume`` is negative.
        RuntimeError: If ffmpeg fails.
    """
    _require_file(video, "Video")
    _require_file(music, "Music")
    if volume < 0:
        raise ValueError(f"volume must be >= 0, got {volume}")
    _ensure_parent(output)

    # normalize=0 keeps the original dialogue at full level; without it amix
    # auto-attenuates both inputs by 1/N and drowns out the video audio.
    filter_complex = (
        f"[1:a]volume={volume}[m];"
        f"[0:a][m]amix=inputs=2:duration=first:normalize=0[a]"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        video,
        "-i",
        music,
        "-filter_complex",
        filter_complex,
        "-map",
        "0:v",
        "-map",
        "[a]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        output,
    ]
    _run_ffmpeg(cmd)
    return output
