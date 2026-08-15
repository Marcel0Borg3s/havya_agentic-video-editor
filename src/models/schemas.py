from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class CreativeBrief(BaseModel):
    product: str
    audience: str
    tone: str
    duration_seconds: int
    style_ref: str | None = None


class MediaAsset(BaseModel):
    """Optional media file incorporated into a generated video."""

    path: str
    role: Literal["opening", "closing", "music", "logo", "other"] = "other"


class EditingOptions(BaseModel):
    """Deterministic/editorial switches for an editing profile."""

    remove_silence: bool = True
    silence_threshold: float = Field(default=0.8, gt=0)
    remove_hesitations: bool = True
    remove_repetitions: bool = True
    detect_bad_takes: bool = True
    detect_scene_changes: bool = True
    transition_type: Literal["cut", "fade", "dissolve"] = "cut"
    transition_duration: float = Field(default=0.3, ge=0, le=5)


class CaptionOptions(BaseModel):
    """Automatic caption rendering preferences."""

    enabled: bool = True
    style: str = "default"
    language: str | None = None
    position: Literal["top", "center", "bottom"] = "bottom"


class OverlayOptions(BaseModel):
    """A timed text or graphic overlay to be rendered by the video engine."""

    role: Literal["title", "subtitle", "subscribe", "credits", "custom"]
    text: str
    start: float = Field(default=0, ge=0)
    duration: float = Field(default=5, gt=0)
    position: Literal["top", "center", "bottom-third", "bottom"] = "bottom-third"
    style: str = "default"

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("overlay text must not be blank")
        return value


class ShortsOptions(BaseModel):
    """Rules for deriving vertical Shorts from the main edit."""

    enabled: bool = True
    count: int = Field(default=3, ge=1, le=20)
    duration_seconds: int = Field(default=60, ge=5, le=180)
    aspect_ratio: Literal["9:16"] = "9:16"
    captions_enabled: bool = True
    cta_enabled: bool = True


class AIOptions(BaseModel):
    """Provider selection without storing credentials in project data."""

    enabled: bool = True
    provider: str = "gemini"
    model: str | None = None
    api_key_env: str | None = None
    base_url: str | None = None


class EditingProfile(BaseModel):
    """User-editable configuration shared by full videos and Shorts."""

    name: str = "youtube-default"
    opening: MediaAsset | None = None
    closing: MediaAsset | None = None
    editing: EditingOptions = Field(default_factory=EditingOptions)
    captions: CaptionOptions = Field(default_factory=CaptionOptions)
    overlays: list[OverlayOptions] = Field(default_factory=list)
    shorts: ShortsOptions = Field(default_factory=ShortsOptions)
    ai: AIOptions = Field(default_factory=AIOptions)


class OutputOptions(BaseModel):
    """Output metadata and format preferences for a render job."""

    full_video_enabled: bool = True
    full_video_aspect_ratio: Literal["16:9", "9:16"] = "16:9"
    title: str | None = None
    channel_name: str | None = None
    credits: str | None = None


class WordTimestamp(BaseModel):
    word: str
    start: float
    end: float


class Shot(BaseModel):
    source_file: str
    start_time: float
    end_time: float
    description: str
    energy_level: int
    relevance_score: float
    transcript: str
    words: list[WordTimestamp] = Field(default_factory=list)
    roll_type: str = Field(
        default="unknown",
        description=(
            "Footage category: 'a-roll' (on-camera talent / talking head), "
            "'b-roll' (cutaway / product / texture / environment), or "
            "'unknown'. Auto-detected from the source directory name during "
            "preprocessing."
        ),
    )


class FootageIndex(BaseModel):
    source_dir: str
    shots: list[Shot]
    total_duration: float
    created_at: datetime


class EditPlanEntry(BaseModel):
    shot_id: str
    start_trim: float
    end_trim: float
    position: int
    text_overlay: str | None = None
    transition: str | None = None


class EditPlan(BaseModel):
    brief: CreativeBrief
    entries: list[EditPlanEntry]
    music_path: str | None = None
    total_duration: float
    # Optional evolution fields. Existing plans remain valid because these
    # fields have defaults and the current renderer can ignore them safely.
    profile: EditingProfile | None = None
    output: OutputOptions = Field(default_factory=OutputOptions)


class ReviewScore(BaseModel):
    adherence: float
    pacing: float
    visual_quality: float
    watchability: float
    overall: float
    feedback: str
