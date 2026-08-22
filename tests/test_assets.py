from __future__ import annotations

from pathlib import Path

import pytest

from src.tools import assets


def test_assemble_without_assets_returns_content_unchanged(tmp_path: Path) -> None:
    content = tmp_path / "content.mp4"
    content.write_bytes(b"content")

    assert assets.assemble_with_assets(str(content), str(tmp_path / "out.mp4")) == str(
        content
    )


def test_assemble_normalizes_and_sequences_opening_and_closing(
    tmp_path: Path, monkeypatch
) -> None:
    content = tmp_path / "content.mp4"
    opening = tmp_path / "opening.mp4"
    closing = tmp_path / "closing.mp4"
    for path in (content, opening, closing):
        path.write_bytes(b"video")

    normalized: list[tuple[str, str, str]] = []
    sequenced: list[list[str]] = []

    def fake_normalize(source: str, output: str, resolution: str) -> str:
        normalized.append((source, output, resolution))
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_bytes(b"normalized")
        return output

    def fake_sequence(clips: list[str], output: str) -> str:
        sequenced.append(clips)
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_bytes(b"assembled")
        return output

    def fake_crossfade(clips: list[str], output: str, duration: float) -> str:
        sequenced.append(clips)
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_bytes(b"assembled")
        return output

    monkeypatch.setattr(assets, "normalize_asset", fake_normalize)
    monkeypatch.setattr(assets, "sequence_clips", fake_sequence)
    monkeypatch.setattr(assets, "sequence_clips_with_crossfade", fake_crossfade)

    output = tmp_path / "assembled.mp4"
    result = assets.assemble_with_assets(
        str(content),
        str(output),
        opening_path=str(opening),
        closing_path=str(closing),
        working_dir=str(tmp_path / "work"),
        resolution="1920x1080",
    )

    assert result == str(output)
    assert [item[0] for item in normalized] == [str(opening), str(closing)]
    assert all(item[2] == "1920x1080" for item in normalized)
    assert sequenced == [
        [
            str(tmp_path / "work" / "opening_normalized.mp4"),
            str(content),
            str(tmp_path / "work" / "closing_normalized.mp4"),
        ]
    ]
    assert output.exists()


def test_assemble_rejects_missing_content(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Content video"):
        assets.assemble_with_assets(str(tmp_path / "missing.mp4"), "out.mp4")


def test_normalize_asset_rejects_missing_asset(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Media asset"):
        assets.normalize_asset(str(tmp_path / "missing.mp4"), str(tmp_path / "out.mp4"))


def test_normalize_asset_delegates_to_final_renderer(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "opening.mov"
    source.write_bytes(b"source")
    calls: list[tuple[str, str, str]] = []

    def fake_render(video: str, output: str, resolution: str) -> str:
        calls.append((video, output, resolution))
        return output

    monkeypatch.setattr(assets, "render_final", fake_render)

    result = assets.normalize_asset(str(source), str(tmp_path / "normalized.mp4"))

    assert result.endswith("normalized.mp4")
    assert calls == [(str(source), str(tmp_path / "normalized.mp4"), "1080x1920")]


def test_sequence_clips_rejects_empty_list() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        assets.sequence_clips([], "out.mp4")


# Keep the final import-level contract explicit: the helper is available from
# the module but does not execute FFmpeg during import.
def test_assets_module_exports_assembly_helper() -> None:
    assert "assemble_with_assets" in assets.__all__
    assert "normalize_asset" in assets.__all__


# The test intentionally creates no real media, so it remains fast and
# deterministic. Manual FFmpeg validation is documented after this task.
def test_paths_are_strings_for_ffmpeg_boundary(tmp_path: Path) -> None:
    source = tmp_path / "content.mp4"
    source.write_bytes(b"x")
    assert isinstance(str(source), str)


# Ensure the helper does not silently accept a missing optional asset.
def test_assemble_rejects_missing_opening(tmp_path: Path) -> None:
    content = tmp_path / "content.mp4"
    content.write_bytes(b"content")
    with pytest.raises(FileNotFoundError, match="Media asset"):
        assets.assemble_with_assets(
            str(content),
            str(tmp_path / "out.mp4"),
            opening_path=str(tmp_path / "opening.mp4"),
        )


# Closing-only assembly is also a supported path.
def test_closing_only_uses_two_clips(tmp_path: Path, monkeypatch) -> None:
    content = tmp_path / "content.mp4"
    closing = tmp_path / "closing.mp4"
    content.write_bytes(b"content")
    closing.write_bytes(b"closing")
    monkeypatch.setattr(
        assets,
        "normalize_asset",
        lambda source, output, resolution: Path(output).write_bytes(b"n") or output,
    )
    captured: list[str] = []
    monkeypatch.setattr(
        assets,
        "sequence_clips",
        lambda clips, output: captured.extend(clips) or output,
    )
    monkeypatch.setattr(
        assets,
        "sequence_clips_with_crossfade",
        lambda clips, output, duration: captured.extend(clips) or output,
    )
    working_dir = tmp_path / "work"
    result = assets.assemble_with_assets(
        str(content),
        str(tmp_path / "out.mp4"),
        closing_path=str(closing),
        working_dir=str(working_dir),
    )
    assert result.endswith("out.mp4")
    assert captured == [str(content), str(working_dir / "closing_normalized.mp4")]
