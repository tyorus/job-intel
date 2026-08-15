"""Tests for tracker FastAPI routes with a fake store."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from jobintel.api.app import app, get_store
from jobintel.config import get_settings
from jobintel.models import (
    JobRead,
    JobStatus,
    ProgressEntityType,
    ProgressEvent,
    Prospect,
)


class FakeStore:
    def __init__(self) -> None:
        self.jobs: dict[UUID, JobRead] = {}
        self.prospects: dict[UUID, Prospect] = {}
        self.events: list[ProgressEvent] = []

    def dashboard(self) -> dict[str, Any]:
        return {
            "jobs_total": len(self.jobs),
            "prospects_total": len(self.prospects),
            "jobs_by_status": {"new": len(self.jobs)},
            "prospects_by_status": {"new": len(self.prospects)},
            "recent_progress": [e.model_dump(mode="json") for e in self.events[:20]],
        }

    def list_jobs(self, **_: Any) -> list[JobRead]:
        return list(self.jobs.values())

    def get_job(self, job_id: UUID) -> JobRead | None:
        return self.jobs.get(job_id)

    def create_job(self, job: Any, company_name: str | None = None) -> JobRead:
        created = JobRead(
            id=uuid4(),
            title=job.title,
            description=job.description,
            url=job.url,
            apply_url=getattr(job, "apply_url", None),
            source=job.source,
            status=JobStatus.NEW,
            company_name=company_name,
            remote_type=job.remote_type,
            posted_at=getattr(job, "posted_at", None),
            deadline_at=getattr(job, "deadline_at", None),
            salary_text=getattr(job, "salary_text", None),
            employment_type=getattr(job, "employment_type", None),
            department=getattr(job, "department", None),
            seniority=getattr(job, "seniority", None),
            tags=list(getattr(job, "tags", []) or []),
            metadata_json=dict(getattr(job, "metadata_json", {}) or {}),
        )
        assert created.id is not None
        self.jobs[created.id] = created
        return created

    def update_job(self, job_id: UUID, fields: dict[str, Any]) -> JobRead:
        current = self.jobs[job_id]
        updated = JobRead.model_validate({**current.model_dump(mode="json"), **fields})
        self.jobs[job_id] = updated
        return updated

    def delete_job(self, job_id: UUID) -> None:
        if job_id not in self.jobs:
            raise KeyError(job_id)
        del self.jobs[job_id]
        self.events = [
            event
            for event in self.events
            if not (event.entity_type == ProgressEntityType.JOB and event.entity_id == job_id)
        ]

    def submit_job_progress(
        self, job_id: UUID, status: JobStatus, note: str | None = None
    ) -> ProgressEvent:
        job = self.jobs[job_id]
        updated = job.model_copy(update={"status": status})
        self.jobs[job_id] = updated
        event = ProgressEvent(
            id=uuid4(),
            entity_type=ProgressEntityType.JOB,
            entity_id=job_id,
            status=status.value,
            note=note,
            created_at=datetime.now(UTC),
        )
        self.events.append(event)
        return event

    def list_prospects(self, **_: Any) -> list[Prospect]:
        return list(self.prospects.values())

    def get_prospect(self, prospect_id: UUID) -> Prospect | None:
        return self.prospects.get(prospect_id)

    def create_prospect(self, prospect: Prospect) -> Prospect:
        created = prospect.model_copy(update={"id": uuid4()})
        assert created.id is not None
        self.prospects[created.id] = created
        return created

    def update_prospect(self, prospect_id: UUID, fields: dict[str, Any]) -> Prospect:
        current = self.prospects[prospect_id]
        updated = current.model_copy(update=fields)
        self.prospects[prospect_id] = updated
        return updated

    def submit_prospect_progress(
        self, prospect_id: UUID, status: Any, note: str | None = None
    ) -> ProgressEvent:
        current = self.prospects[prospect_id]
        self.prospects[prospect_id] = current.model_copy(update={"status": status})
        event = ProgressEvent(
            id=uuid4(),
            entity_type=ProgressEntityType.PROSPECT,
            entity_id=prospect_id,
            status=status.value,
            note=note,
            created_at=datetime.now(UTC),
        )
        self.events.append(event)
        return event

    def list_progress(self, **_: Any) -> list[ProgressEvent]:
        return list(self.events)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("TRACKER_API_KEY", "test-key")
    get_settings.cache_clear()
    store = FakeStore()
    app.dependency_overrides[get_store] = lambda: store
    with TestClient(app) as test_client:
        test_client.store = store  # type: ignore[attr-defined]
        yield test_client
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def _auth() -> dict[str, str]:
    return {"X-Api-Key": "test-key"}


def test_health_open() -> None:
    with TestClient(app) as test_client:
        response = test_client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_dashboard_requires_key(client: TestClient) -> None:
    assert client.get("/api/dashboard").status_code == 401
    response = client.get("/api/dashboard", headers=_auth())
    assert response.status_code == 200
    assert response.json()["jobs_total"] == 0


def test_create_job_and_progress(client: TestClient) -> None:
    created = client.post(
        "/api/jobs",
        headers=_auth(),
        json={
            "title": "Data Engineer",
            "company_name": "Harbor",
            "description": "Python pipelines",
            "source": "linkedin",
            "url": "https://linkedin.com/jobs/view/1",
        },
    )
    assert created.status_code == 201
    job_id = created.json()["id"]
    progress = client.post(
        f"/api/jobs/{job_id}/progress",
        headers=_auth(),
        json={"status": "applied", "note": "Sent via LinkedIn Easy Apply"},
    )
    assert progress.status_code == 201
    assert progress.json()["status"] == "applied"
    listed = client.get("/api/jobs", headers=_auth())
    assert listed.json()[0]["status"] == "applied"


def test_create_prospect_and_progress(client: TestClient) -> None:
    created = client.post(
        "/api/prospects",
        headers=_auth(),
        json={
            "name": "Alex Ops",
            "company": "Northwind Agency",
            "package": "brief",
            "channel": "linkedin",
        },
    )
    assert created.status_code == 201
    prospect_id = created.json()["id"]
    progress = client.post(
        f"/api/prospects/{prospect_id}/progress",
        headers=_auth(),
        json={"status": "contacted", "note": "Sent connection note"},
    )
    assert progress.status_code == 201
    assert client.get("/api/progress", headers=_auth()).json()[0]["entity_type"] == "prospect"


def test_job_not_related_and_prospect_cancelled(client: TestClient) -> None:
    job = client.post(
        "/api/jobs",
        headers=_auth(),
        json={"title": "Unrelated Sales Role", "description": "Quota hunting"},
    ).json()
    dismiss = client.post(
        f"/api/jobs/{job['id']}/progress",
        headers=_auth(),
        json={"status": "not_related", "note": "Not data/engineering"},
    )
    assert dismiss.status_code == 201
    assert dismiss.json()["status"] == "not_related"

    prospect = client.post(
        "/api/prospects",
        headers=_auth(),
        json={"name": "Ghost Lead", "company": "Nowhere Inc"},
    ).json()
    cancelled = client.post(
        f"/api/prospects/{prospect['id']}/progress",
        headers=_auth(),
        json={"status": "cancelled", "note": "Budget frozen"},
    )
    assert cancelled.status_code == 201
    assert cancelled.json()["status"] == "cancelled"


def test_job_metadata_create_and_patch(client: TestClient) -> None:
    created = client.post(
        "/api/jobs",
        headers=_auth(),
        json={
            "title": "Data Engineer",
            "description": "Pipelines",
            "company_name": "Harbor",
            "posted_at": "2026-08-01T00:00:00Z",
            "deadline_at": "2026-08-20T00:00:00Z",
            "salary_text": "$100k",
            "employment_type": "full-time",
            "tags": ["python", "etl"],
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["posted_at"].startswith("2026-08-01")
    assert body["deadline_at"].startswith("2026-08-20")
    assert body["salary_text"] == "$100k"
    assert body["tags"] == ["python", "etl"]

    patched = client.patch(
        f"/api/jobs/{body['id']}",
        headers=_auth(),
        json={"deadline_at": "2026-08-25T00:00:00Z", "seniority": "mid"},
    )
    assert patched.status_code == 200
    assert patched.json()["seniority"] == "mid"
    assert patched.json()["deadline_at"].startswith("2026-08-25")


def test_delete_job(client: TestClient) -> None:
    created = client.post(
        "/api/jobs",
        headers=_auth(),
        json={"title": "Drop me", "description": "Gone"},
    )
    job_id = created.json()["id"]
    deleted = client.delete(f"/api/jobs/{job_id}", headers=_auth())
    assert deleted.status_code == 204
    missing = client.get(f"/api/jobs/{job_id}", headers=_auth())
    assert missing.status_code == 404
    listed = client.get("/api/jobs", headers=_auth())
    assert all(row["id"] != job_id for row in listed.json())
    missing_delete = client.delete(
        "/api/jobs/00000000-0000-0000-0000-000000000000",
        headers=_auth(),
    )
    assert missing_delete.status_code == 404


def test_invalid_job_status(client: TestClient) -> None:
    created = client.post(
        "/api/jobs",
        headers=_auth(),
        json={"title": "Role", "description": "Desc"},
    )
    job_id = created.json()["id"]
    response = client.post(
        f"/api/jobs/{job_id}/progress",
        headers=_auth(),
        json={"status": "nope"},
    )
    assert response.status_code == 400

