from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.models.schemas import (
    AIOptions,
    CreativeBrief,
    EditingProfile,
    EditPlan,
    EditPlanEntry,
    MediaAsset,
    OverlayOptions,
    OutputOptions,
    ShortsOptions,
)


def _brief() -> CreativeBrief:
    return CreativeBrief(
        product="Personal channel",
        audience="YouTube viewers",
        tone="clear",
        duration_seconds=600,
    )


def _entry() -> EditPlanEntry:
    return EditPlanEntry(
        shot_id="video.mp4#0.0",
        start_trim=0.0,
        end_trim=10.0,
        position=0,
    )


def test_default_editing_profile_is_ready_for_youtube() -> None:
    profile = EditingProfile()

    assert profile.name == "youtube-default"
    assert profile.opening is None
    assert profile.closing is None
    assert profile.editing.remove_silence is True
    assert profile.captions.enabled is True
    assert profile.shorts.enabled is True
    assert profile.shorts.aspect_ratio == "9:16"
    assert profile.ai.provider == "gemini"


def test_profile_supports_opening_closing_overlays_and_output_metadata() -> None:
    profile = EditingProfile(
        opening=MediaAsset(path="assets/opening.mp4", role="opening"),
        closing=MediaAsset(path="assets/closing.mp4", role="closing"),
        overlays=[
            OverlayOptions(role="title", text="Meu vídeo", duration=4),
            OverlayOptions(
                role="subscribe",
                text="Inscreva-se no canal",
                start=120,
                duration=6,
            ),
        ],
        shorts=ShortsOptions(count=5, duration_seconds=45),
        ai=AIOptions(provider="custom", model="my-editor"),
    )
    output = OutputOptions(
        title="Meu vídeo completo",
        channel_name="Meu Canal",
        credits="Produção pessoal",
    )

    assert profile.opening is not None
    assert profile.opening.role == "opening"
    assert profile.closing is not None
    assert len(profile.overlays) == 2
    assert profile.shorts.count == 5
    assert profile.ai.provider == "custom"
    assert output.channel_name == "Meu Canal"


def test_overlay_text_must_not_be_blank() -> None:
    with pytest.raises(ValidationError):
        OverlayOptions(role="title", text="   ")


def test_shorts_options_reject_invalid_duration_and_count() -> None:
    with pytest.raises(ValidationError):
        ShortsOptions(count=0)
    with pytest.raises(ValidationError):
        ShortsOptions(duration_seconds=181)


def test_legacy_edit_plan_remains_valid_without_profile() -> None:
    plan = EditPlan(
        brief=_brief(),
        entries=[_entry()],
        total_duration=10.0,
    )

    assert plan.profile is None
    assert plan.output.full_video_enabled is True
    assert plan.output.full_video_aspect_ratio == "16:9"
    assert plan.entries[0].shot_id == "video.mp4#0.0"


def test_edit_plan_can_carry_profile_and_output_options() -> None:
    profile = EditingProfile(name="my-youtube-profile")
    plan = EditPlan(
        brief=_brief(),
        entries=[_entry()],
        total_duration=10.0,
        profile=profile,
        output=OutputOptions(full_video_aspect_ratio="16:9"),
    )

    assert plan.profile is not None
    assert plan.profile.name == "my-youtube-profile"
    assert plan.output.full_video_aspect_ratio == "16:9"


def test_profile_serialization_does_not_create_api_key_field() -> None:
    payload = EditingProfile().model_dump()

    assert "api_key" not in payload
    assert "api_key_env" in payload["ai"]
