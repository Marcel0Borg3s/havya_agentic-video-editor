"""Load and validate user editing profiles from YAML files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from src.models.schemas import EditingProfile


def load_editing_profile(profile_path: str | Path) -> EditingProfile:
    """Load a YAML editing profile and validate it with Pydantic.

    Unlike the optional style-skill loader used by the Director, an editing
    profile is an execution contract. Missing, malformed, or invalid files
    therefore raise clear exceptions instead of silently falling back.
    """
    path = Path(profile_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"editing profile does not exist: {profile_path}")
    if not path.is_file():
        raise ValueError(f"editing profile is not a file: {profile_path}")

    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise OSError(f"could not read editing profile {profile_path!r}: {exc}") from exc

    if not raw_text.strip():
        raise ValueError(f"editing profile {profile_path!r} is empty")

    try:
        payload: Any = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise ValueError(
            f"editing profile {profile_path!r} is not valid YAML: {exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise ValueError(
            f"editing profile {profile_path!r} must be a mapping, "
            f"got {type(payload).__name__}"
        )

    try:
        return EditingProfile.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(
            f"editing profile {profile_path!r} failed validation: {exc}"
        ) from exc


def dump_editing_profile(profile: EditingProfile, profile_path: str | Path) -> str:
    """Serialize a validated profile to YAML and write it to disk."""
    path = Path(profile_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = profile.model_dump(exclude_none=True)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return str(path)
