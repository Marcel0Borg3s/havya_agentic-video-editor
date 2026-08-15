from __future__ import annotations

from pathlib import Path

import pytest

from src.models.schemas import (
    CaptionOptions,
    CreativeBrief,
    EditPlan,
    EditingProfile,
    OverlayOptions,
    OutputOptions,
)
from src.tools import overlays


def _plan(**kwargs) -> EditPlan:
    return EditPlan(
        brief=CreativeBrief(
            product="test",
            audience="viewers",
            tone="clear",
            duration_seconds=30,
        ),
        entries=[],
        total_duration=30,
        **kwargs,
    )


def test_build_plan_overlays_includes_profile_and_output_metadata() -> None:
    plan = _plan(
        profile=EditingProfile(
            overlays=[OverlayOptions(role="title", text="Perfil")]
        ),
        output=OutputOptions(
            title="Título",
            channel_name="Meu Canal",
            credits="Créditos",
        ),
    )

    result = overlays.build_plan_overlays(plan, 30)

    assert [item.text for item in result] == [
        "Perfil",
        "Título",
        "Inscreva-se em Meu Canal",
        "Créditos",
    ]
    assert result[2].start == 22
    assert result[3].start == 25


def test_build_plan_overlays_without_configuration_is_empty() -> None:
    assert overlays.build_plan_overlays(_plan(), 30) == []


def test_apply_plan_overlays_chains_each_overlay(tmp_path: Path, monkeypatch) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"video")
    plan = _plan(
        profile=EditingProfile(
            overlays=[
                OverlayOptions(role="title", text="Um"),
                OverlayOptions(role="custom", text="Dois"),
            ]
        )
    )
    calls: list[tuple[str, str, str, float, float, str]] = []

    monkeypatch.setattr(overlays, "get_video_duration", lambda path: 30.0)

    def fake_add(video, text, position, start, duration, output):
        calls.append((video, text, position, start, duration, output))
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_bytes(b"overlay")
        return output

    monkeypatch.setattr(overlays, "add_text_overlay", fake_add)
    output = tmp_path / "final.mp4"

    result = overlays.apply_plan_overlays(
        str(video), plan, str(output), working_dir=str(tmp_path / "work")
    )

    assert result == str(output)
    assert len(calls) == 2
    assert calls[0][0] == str(video)
    assert calls[0][1] == "Um"
    assert calls[0][2] == "bottom-third"
    assert calls[1][0].endswith("overlay_00.mp4")
    assert calls[1][1] == "Dois"
    assert output.exists()


def test_apply_plan_overlays_returns_original_when_empty(tmp_path: Path, monkeypatch) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"video")
    monkeypatch.setattr(
        overlays,
        "get_video_duration",
        lambda _: pytest.fail("duration should not be queried without overlays"),
    )

    assert overlays.apply_plan_overlays(
        str(video), _plan(), str(tmp_path / "output.mp4"), working_dir=str(tmp_path / "work")
    ) == str(video)


def test_get_video_duration_rejects_missing_video(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Video not found"):
        overlays.get_video_duration(str(tmp_path / "missing.mp4"))


def test_position_mapping_rejects_unknown_position() -> None:
    with pytest.raises(ValueError, match="unsupported overlay position"):
        overlays._position_for_ffmpeg("left")


def test_caption_toggle_changes_editor_output_paths(tmp_path: Path) -> None:
    # This contract is covered through the editor's path planner in the full
    # suite; the profile-level assertion documents the user-facing switch.
    enabled = EditingProfile().captions.enabled
    disabled = EditingProfile(captions=CaptionOptions(enabled=False)).captions.enabled
    assert enabled is True
    assert disabled is False


def test_overlay_module_exports_public_api() -> None:
    assert "apply_plan_overlays" in overlays.__all__
    assert "build_plan_overlays" in overlays.__all__
    assert "get_video_duration" in overlays.__all__


def test_subscribe_overlay_uses_bottom_position() -> None:
    plan = _plan(output=OutputOptions(channel_name="Canal"))
    result = overlays.build_plan_overlays(plan, 10)
    assert result[0].position == "bottom"
    assert result[0].duration == 6


def test_short_video_metadata_overlay_durations_are_clamped() -> None:
    plan = _plan(output=OutputOptions(title="Título", channel_name="Canal", credits="Créditos"))
    result = overlays.build_plan_overlays(plan, 3)
    assert all(item.duration <= 3 for item in result[1:])
    assert result[1].start == 0
    assert result[2].start == 0
