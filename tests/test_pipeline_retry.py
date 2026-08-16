from __future__ import annotations

import pytest

from src.pipeline.runner import _is_quota_exhausted, _with_transient_retry


def test_quota_exhaustion_is_detected() -> None:
    assert _is_quota_exhausted(Exception("429 RESOURCE_EXHAUSTED quota exceeded"))
    assert not _is_quota_exhausted(Exception("temporary server failure"))


def test_quota_exhaustion_does_not_wait_or_retry(monkeypatch) -> None:
    calls = 0

    def failing_call():
        nonlocal calls
        calls += 1
        raise RuntimeError("429 RESOURCE_EXHAUSTED quota exceeded")

    monkeypatch.setattr("src.pipeline.runner.time.sleep", lambda _: pytest.fail("must not sleep"))

    with pytest.raises(RuntimeError, match="quota exhausted"):
        _with_transient_retry(failing_call)
    assert calls == 1
