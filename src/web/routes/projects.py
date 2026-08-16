"""Project management routes for generalized footage ingestion.

A project wraps a footage directory with an automatically generated
FootageIndex. Users create a project by pointing at a local folder of
video files; the backend runs ``preprocess_footage()`` asynchronously
and tracks status until the index is ready.

The in-memory ``ProjectStore`` mirrors the ``JobRegistry`` pattern --
dict keyed by UUID, no external persistence, single-process scope.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from src.models.schemas import FootageIndex
from src.pipeline.preprocess import preprocess_footage

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = REPO_ROOT / "output"
UPLOADS_DIR = OUTPUT_DIR / "uploads"
VIDEO_SUFFIXES = {".mov", ".mp4", ".m4v", ".mkv"}
MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024

router = APIRouter(tags=["projects"])


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Project:
    id: str
    name: str
    footage_dir: str
    footage_index_path: str
    status: str  # "preprocessing" | "ready" | "failed"
    shot_count: int = 0
    total_duration: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None
    opening_path: str | None = None
    closing_path: str | None = None

    def summary(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "footage_dir": self.footage_dir,
            "footage_index_path": self.footage_index_path,
            "status": self.status,
            "shot_count": self.shot_count,
            "total_duration": self.total_duration,
            "created_at": self.created_at.isoformat(),
            "error": self.error,
            "opening_path": self.opening_path,
            "closing_path": self.closing_path,
        }


# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------

class ProjectStore:
    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}

    def get(self, project_id: str) -> Project | None:
        return self._projects.get(project_id)

    def list_projects(self) -> list[Project]:
        return sorted(self._projects.values(), key=lambda p: p.created_at)

    def create(self, name: str, footage_dir: str) -> Project:
        project_id = str(uuid.uuid4())
        index_dir = OUTPUT_DIR / "projects" / project_id
        index_dir.mkdir(parents=True, exist_ok=True)
        footage_index_path = str(index_dir / "footage_index.json")

        project = Project(
            id=project_id,
            name=name,
            footage_dir=footage_dir,
            footage_index_path=footage_index_path,
            status="preprocessing",
        )
        self._projects[project_id] = project
        return project

    def delete(self, project_id: str) -> bool:
        return self._projects.pop(project_id, None) is not None


# Singleton -- attached to app.state in lifespan, but also usable directly.
_store = ProjectStore()


def get_store() -> ProjectStore:
    return _store


# ---------------------------------------------------------------------------
# Background preprocessing
# ---------------------------------------------------------------------------

async def _run_preprocessing(project: Project) -> None:
    """Run ``preprocess_footage`` in a thread and update project status."""
    try:
        await asyncio.to_thread(
            preprocess_footage,
            input_dir=project.footage_dir,
            output_path=project.footage_index_path,
        )
        # Read back the index to populate shot_count and total_duration.
        index_path = Path(project.footage_index_path)
        if index_path.is_file():
            index = FootageIndex.model_validate_json(index_path.read_text("utf-8"))
            project.shot_count = len(index.shots)
            project.total_duration = index.total_duration
        project.status = "ready"
        logger.info("Project %s preprocessing complete: %d shots", project.id, project.shot_count)
    except Exception as exc:
        project.status = "failed"
        project.error = str(exc)
        logger.exception("Project %s preprocessing failed", project.id)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class CreateProjectRequest(BaseModel):
    name: str
    footage_dir: str


class CreateProjectResponse(BaseModel):
    id: str
    name: str
    status: str


async def _save_upload(upload: UploadFile, destination: Path) -> str:
    """Save one validated upload without trusting the client filename."""
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in VIDEO_SUFFIXES:
        raise HTTPException(status_code=422, detail=f"Unsupported video type: {suffix or 'unknown'}")
    destination = destination.with_suffix(suffix)
    total = 0
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with destination.open("wb") as target:
            while chunk := await upload.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="Uploaded video exceeds the 2 GB limit")
                target.write(chunk)
    finally:
        await upload.close()
    return str(destination)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/api/projects", response_model=CreateProjectResponse, status_code=202)
async def create_project(body: CreateProjectRequest) -> CreateProjectResponse:
    footage_path = Path(body.footage_dir).expanduser().resolve()
    if not footage_path.is_dir():
        raise HTTPException(status_code=422, detail=f"Directory does not exist: {body.footage_dir}")

    store = get_store()
    project = store.create(name=body.name, footage_dir=str(footage_path))

    # Fire-and-forget preprocessing task.
    asyncio.create_task(_run_preprocessing(project))

    return CreateProjectResponse(id=project.id, name=project.name, status=project.status)


@router.post("/api/projects/upload", response_model=CreateProjectResponse, status_code=202)
async def upload_project(
    name: str = Form(...),
    raw_video: UploadFile = File(...),
    opening: UploadFile | None = File(default=None),
    closing: UploadFile | None = File(default=None),
) -> CreateProjectResponse:
    """Create a project from raw video and optional intro/outro assets."""
    project_id = str(uuid.uuid4())
    project_dir = UPLOADS_DIR / project_id
    footage_dir = project_dir / "footage"
    try:
        await _save_upload(raw_video, footage_dir / "raw")
        opening_path = await _save_upload(opening, project_dir / "opening" / "opening") if opening is not None else None
        closing_path = await _save_upload(closing, project_dir / "closing" / "closing") if closing is not None else None
    except Exception:
        import shutil
        shutil.rmtree(project_dir, ignore_errors=True)
        raise

    store = get_store()
    project = Project(
        id=project_id,
        name=name.strip() or "Novo vídeo",
        footage_dir=str(footage_dir),
        footage_index_path=str(OUTPUT_DIR / "projects" / project_id / "footage_index.json"),
        status="preprocessing",
        opening_path=opening_path,
        closing_path=closing_path,
    )
    store._projects[project_id] = project
    asyncio.create_task(_run_preprocessing(project))
    return CreateProjectResponse(id=project.id, name=project.name, status=project.status)


@router.get("/api/projects")
async def list_projects() -> list[dict]:
    store = get_store()
    return [p.summary() for p in store.list_projects()]


@router.get("/api/projects/{project_id}")
async def get_project(project_id: str) -> dict:
    store = get_store()
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project.summary()


@router.delete("/api/projects/{project_id}", status_code=204)
async def delete_project(project_id: str) -> None:
    store = get_store()
    if not store.delete(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
