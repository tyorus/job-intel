"""FastAPI app: tracker CRUD for jobs and client prospects."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from jobintel.api.schemas import (
    JobCreate,
    JobDismissIn,
    JobUpdate,
    ProgressIn,
    ProspectCreate,
    ProspectUpdate,
)
from jobintel.config import Settings, get_settings
from jobintel.db import get_store as build_store
from jobintel.models import Job, JobStatus, ProgressEntityType, Prospect, ProspectStatus

app = FastAPI(title="Job Intelligence Tracker", version="0.1.0")

# backend/jobintel/api/app.py -> parents[3] = repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]
_FRONTEND_DIST = _REPO_ROOT / "frontend" / "dist"
_PUBLIC_DIR = _REPO_ROOT / "public"


def _configure_cors(application: FastAPI, settings: Settings) -> None:
    origins = settings.cors_origin_list
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


_configure_cors(app, get_settings())


def get_store() -> object:
    return build_store()


def require_api_key(
    x_api_key: Annotated[str | None, Header()] = None,
) -> None:
    expected = get_settings().tracker_api_key
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TRACKER_API_KEY is not configured",
        )
    if not x_api_key or x_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )


Auth = Annotated[None, Depends(require_api_key)]
Db = Annotated[object, Depends(get_store)]


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/dashboard")
def dashboard(_: Auth, store: Db) -> dict:
    return store.dashboard()


@app.get("/api/jobs")
def list_jobs(
    _: Auth,
    store: Db,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    source: str | None = None,
    q: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    jobs = store.list_jobs(status=status_filter, source=source, q=q, limit=limit, offset=offset)
    return [job.model_dump(mode="json") for job in jobs]


@app.post("/api/jobs/not-related")
def dismiss_jobs(_: Auth, store: Db, body: JobDismissIn) -> dict:
    dismiss = getattr(store, "dismiss_job", store.delete_job)
    dismissed: list[str] = []
    missing: list[str] = []
    for job_id in body.job_ids:
        try:
            dismiss(job_id)
            dismissed.append(str(job_id))
        except KeyError:
            missing.append(str(job_id))
    return {"dismissed": dismissed, "missing": missing}


@app.get("/api/jobs/{job_id}")
def get_job(_: Auth, store: Db, job_id: UUID) -> dict:
    job = store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.model_dump(mode="json")


@app.post("/api/jobs", status_code=201)
def create_job(_: Auth, store: Db, body: JobCreate) -> dict:
    job = Job(
        title=body.title,
        description=body.description,
        url=body.url,
        apply_url=body.apply_url,
        location=body.location,
        country=body.country,
        remote_type=body.remote_type,
        source=body.source,
        posted_at=body.posted_at,
        deadline_at=body.deadline_at,
        salary_text=body.salary_text,
        employment_type=body.employment_type,
        department=body.department,
        seniority=body.seniority,
        tags=body.tags,
        metadata_json=body.metadata_json,
        status=JobStatus.NEW,
    )
    created = store.create_job(job, company_name=body.company_name)
    if body.notes and created.id:
        store.submit_job_progress(created.id, JobStatus.NEW, body.notes)
        created = store.get_job(created.id) or created
    return created.model_dump(mode="json")


@app.patch("/api/jobs/{job_id}")
def update_job(_: Auth, store: Db, job_id: UUID, body: JobUpdate) -> dict:
    fields = body.model_dump(mode="json", exclude_unset=True)
    try:
        updated = store.update_job(job_id, fields)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    return updated.model_dump(mode="json")


@app.delete("/api/jobs/{job_id}", status_code=204)
def delete_job(_: Auth, store: Db, job_id: UUID) -> None:
    try:
        store.delete_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc


@app.post("/api/jobs/{job_id}/progress", status_code=201)
def job_progress(_: Auth, store: Db, job_id: UUID, body: ProgressIn) -> dict:
    try:
        status_value = JobStatus(body.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid job status: {body.status}") from exc
    try:
        if status_value == JobStatus.NOT_RELATED:
            dismiss = getattr(store, "dismiss_job", store.delete_job)
            dismiss(job_id)
            return {
                "entity_type": ProgressEntityType.JOB.value,
                "entity_id": str(job_id),
                "status": status_value.value,
                "note": body.note,
            }
        event = store.submit_job_progress(job_id, status_value, body.note)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    return event.model_dump(mode="json")


@app.get("/api/prospects")
def list_prospects(
    _: Auth,
    store: Db,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    package: str | None = None,
    q: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    rows = store.list_prospects(
        status=status_filter, package=package, q=q, limit=limit, offset=offset
    )
    return [row.model_dump(mode="json") for row in rows]


@app.get("/api/prospects/{prospect_id}")
def get_prospect(_: Auth, store: Db, prospect_id: UUID) -> dict:
    row = store.get_prospect(prospect_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Prospect not found")
    return row.model_dump(mode="json")


@app.post("/api/prospects", status_code=201)
def create_prospect(_: Auth, store: Db, body: ProspectCreate) -> dict:
    created = store.create_prospect(Prospect.model_validate(body.model_dump()))
    return created.model_dump(mode="json")


@app.patch("/api/prospects/{prospect_id}")
def update_prospect(_: Auth, store: Db, prospect_id: UUID, body: ProspectUpdate) -> dict:
    fields = body.model_dump(mode="json", exclude_unset=True)
    try:
        updated = store.update_prospect(prospect_id, fields)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Prospect not found") from exc
    return updated.model_dump(mode="json")


@app.post("/api/prospects/{prospect_id}/progress", status_code=201)
def prospect_progress(_: Auth, store: Db, prospect_id: UUID, body: ProgressIn) -> dict:
    try:
        status_value = ProspectStatus(body.status)
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail=f"Invalid prospect status: {body.status}"
        ) from exc
    try:
        event = store.submit_prospect_progress(prospect_id, status_value, body.note)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Prospect not found") from exc
    return event.model_dump(mode="json")


@app.get("/api/progress")
def list_progress(
    _: Auth,
    store: Db,
    entity_type: ProgressEntityType | None = None,
    entity_id: UUID | None = None,
    since: str | None = None,
    limit: int = 50,
) -> list[dict]:
    events = store.list_progress(
        entity_type=entity_type.value if entity_type else None,
        entity_id=entity_id,
        since=since,
        limit=limit,
    )
    return [event.model_dump(mode="json") for event in events]


def _mount_frontend() -> None:
    """Serve the Vue build from FastAPI on Vercel (single entrypoint)."""
    static_dir = _PUBLIC_DIR if (_PUBLIC_DIR / "index.html").is_file() else _FRONTEND_DIST
    if not static_dir.is_dir() or not (static_dir / "index.html").is_file():
        return
    assets = static_dir / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

    @app.get("/")
    def spa_root() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str) -> FileResponse:
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = static_dir / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(static_dir / "index.html")


_mount_frontend()
