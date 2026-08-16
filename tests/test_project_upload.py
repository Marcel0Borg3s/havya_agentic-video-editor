from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src.web.app import app
from src.web.routes import projects as projects_module


def test_upload_project_rejects_unsupported_raw_video(tmp_path: Path) -> None:
    projects_module.UPLOADS_DIR = tmp_path / "uploads"
    projects_module.OUTPUT_DIR = tmp_path / "output"
    with TestClient(app) as client:
        response = client.post(
            "/api/projects/upload",
            data={"name": "Invalid"},
            files={"raw_video": ("notes.txt", b"not video", "text/plain")},
        )
    assert response.status_code == 422
    assert "Unsupported video type" in response.json()["detail"]


def test_upload_project_saves_raw_intro_and_closing(tmp_path: Path, monkeypatch) -> None:
    projects_module.UPLOADS_DIR = tmp_path / "uploads"
    projects_module.OUTPUT_DIR = tmp_path / "output"
    async def fake_preprocessing(project):
        return None

    monkeypatch.setattr(projects_module, "_run_preprocessing", fake_preprocessing)

    with TestClient(app) as client:
        response = client.post(
            "/api/projects/upload",
            data={"name": "Uploaded video"},
            files={
                "raw_video": ("raw.mp4", b"raw", "video/mp4"),
                "opening": ("intro.mov", b"intro", "video/quicktime"),
                "closing": ("outro.mkv", b"outro", "video/x-matroska"),
            },
        )

    assert response.status_code == 202
    project_id = response.json()["id"]
    project_dir = tmp_path / "uploads" / project_id
    assert (project_dir / "footage" / "raw.mp4").read_bytes() == b"raw"
    assert (project_dir / "opening" / "opening.mov").read_bytes() == b"intro"
    assert (project_dir / "closing" / "closing.mkv").read_bytes() == b"outro"


def test_upload_project_requires_raw_video(tmp_path: Path) -> None:
    projects_module.UPLOADS_DIR = tmp_path / "uploads"
    with TestClient(app) as client:
        response = client.post("/api/projects/upload", data={"name": "Missing"})
    assert response.status_code == 422
    assert "raw_video" in response.text
