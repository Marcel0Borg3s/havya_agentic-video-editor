from __future__ import annotations

from pathlib import Path

import yaml

from src.models.schemas import CreativeBrief, EditPlan, EditPlanEntry
from src.pipeline import runner


def _brief() -> CreativeBrief:
    return CreativeBrief(
        product="profile-test",
        audience="viewers",
        tone="clear",
        duration_seconds=10,
    )


def _plan() -> EditPlan:
    return EditPlan(
        brief=_brief(),
        entries=[
            EditPlanEntry(
                shot_id="video.mp4#0.0",
                start_trim=0,
                end_trim=10,
                position=0,
            )
        ],
        total_duration=10,
    )


def test_run_pipeline_attaches_profile_to_director_plan(
    tmp_path: Path, monkeypatch
) -> None:
    pipeline_path = tmp_path / "pipeline.yaml"
    pipeline_path.write_text(
        yaml.safe_dump({"name": "profile-test", "steps": [{"agent": "director"}]}),
        encoding="utf-8",
    )
    footage_index_path = tmp_path / "footage_index.json"
    footage_index_path.write_text("{}", encoding="utf-8")
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(
        "name: test-profile\nshorts:\n  count: 2\n", encoding="utf-8"
    )

    monkeypatch.setattr(runner, "run_director", lambda brief, index: _plan())

    result = runner.run_pipeline(
        str(pipeline_path),
        _brief(),
        str(footage_index_path),
        human_approval=False,
        profile_path=str(profile_path),
    )

    assert result.edit_plan is not None
    assert result.edit_plan.profile is not None
    assert result.edit_plan.profile.name == "test-profile"
    assert result.edit_plan.profile.shorts.count == 2


def test_run_pipeline_rejects_invalid_profile_before_running_agents(
    tmp_path: Path, monkeypatch
) -> None:
    pipeline_path = tmp_path / "pipeline.yaml"
    pipeline_path.write_text(
        yaml.safe_dump({"steps": [{"agent": "director"}]}), encoding="utf-8"
    )
    footage_index_path = tmp_path / "footage_index.json"
    footage_index_path.write_text("{}", encoding="utf-8")
    profile_path = tmp_path / "invalid.yaml"
    profile_path.write_text("shorts:\n  count: 0\n", encoding="utf-8")

    called = False

    def fake_director(brief, index):
        nonlocal called
        called = True
        return _plan()

    monkeypatch.setattr(runner, "run_director", fake_director)

    try:
        runner.run_pipeline(
            str(pipeline_path),
            _brief(),
            str(footage_index_path),
            human_approval=False,
            profile_path=str(profile_path),
        )
    except ValueError as exc:
        assert "failed validation" in str(exc)
    else:
        raise AssertionError("invalid profile should fail")

    assert called is False
