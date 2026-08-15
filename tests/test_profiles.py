from __future__ import annotations

from pathlib import Path

import pytest

from src.models.schemas import EditingProfile
from src.pipeline.profiles import dump_editing_profile, load_editing_profile


def test_load_editing_profile_from_yaml(tmp_path: Path) -> None:
    path = tmp_path / "profile.yaml"
    path.write_text(
        """
name: personal
editing:
  remove_silence: false
shorts:
  count: 2
  duration_seconds: 30
ai:
  enabled: false
  provider: none
""",
        encoding="utf-8",
    )

    profile = load_editing_profile(path)

    assert profile.name == "personal"
    assert profile.editing.remove_silence is False
    assert profile.shorts.count == 2
    assert profile.shorts.duration_seconds == 30
    assert profile.ai.enabled is False
    assert profile.ai.provider == "none"


def test_load_editing_profile_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_editing_profile(tmp_path / "missing.yaml")


def test_load_editing_profile_rejects_invalid_yaml_contract(tmp_path: Path) -> None:
    path = tmp_path / "invalid.yaml"
    path.write_text("shorts:\n  count: 0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="failed validation"):
        load_editing_profile(path)


def test_load_editing_profile_rejects_non_mapping(tmp_path: Path) -> None:
    path = tmp_path / "scalar.yaml"
    path.write_text("just-a-string\n", encoding="utf-8")

    with pytest.raises(ValueError, match="must be a mapping"):
        load_editing_profile(path)


def test_dump_and_reload_editing_profile(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "profile.yaml"
    original = EditingProfile(name="round-trip")

    written_path = dump_editing_profile(original, path)
    loaded = load_editing_profile(written_path)

    assert Path(written_path) == path
    assert loaded == original
