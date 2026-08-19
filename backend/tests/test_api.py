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
    Post,
    PostStatus,
    ProgressEntityType,
    ProgressEvent,
    Prospect,
    dump_progress_with_labels,
)


class FakeStore:
    def __init__(self) -> None:
        self.jobs: dict[UUID, JobRead] = {}
        self.prospects: dict[UUID, Prospect] = {}
        self.posts: dict[UUID, Post] = {}
        self.events: list[ProgressEvent] = []

    def dashboard(self) -> dict[str, Any]:
        labels: dict[str, tuple[str | None, str | None]] = {}
        for job in self.jobs.values():
            if job.id is not None:
                labels[str(job.id)] = (job.title, job.company_name)
        for prospect in self.prospects.values():
            if prospect.id is not None:
                labels[str(prospect.id)] = (prospect.name, prospect.company)
        for post in self.posts.values():
            if post.id is not None:
                subtitle = " · ".join(channel.value for channel in post.channels) or None
                labels[str(post.id)] = (post.title, subtitle)
        return {
            "jobs_total": len(self.jobs),
            "prospects_total": len(self.prospects),
            "posts_total": len(self.posts),
            "jobs_by_status": {"new": len(self.jobs)},
            "prospects_by_status": {"new": len(self.prospects)},
            "posts_by_status": {"idea": len(self.posts)},
            "recent_progress": dump_progress_with_labels(self.events[:20], labels),
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

    def dismiss_job(self, job_id: UUID) -> None:
        self.delete_job(job_id)

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

    def list_posts(self, **_: Any) -> list[Post]:
        return list(self.posts.values())

    def get_post(self, post_id: UUID) -> Post | None:
        return self.posts.get(post_id)

    def create_post(self, post: Post) -> Post:
        created = post.model_copy(update={"id": uuid4()})
        assert created.id is not None
        self.posts[created.id] = created
        return created

    def update_post(self, post_id: UUID, fields: dict[str, Any]) -> Post:
        current = self.posts[post_id]
        updated = current.model_copy(update=fields)
        self.posts[post_id] = updated
        return updated

    def submit_post_progress(
        self, post_id: UUID, status: PostStatus, note: str | None = None
    ) -> ProgressEvent:
        current = self.posts[post_id]
        updates: dict[str, Any] = {"status": status}
        if status == PostStatus.PUBLISHED and not current.published_at:
            updates["published_at"] = datetime.now(UTC)
        self.posts[post_id] = current.model_copy(update=updates)
        event = ProgressEvent(
            id=uuid4(),
            entity_type=ProgressEntityType.POST,
            entity_id=post_id,
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
    board = client.get("/api/dashboard", headers=_auth())
    recent = board.json()["recent_progress"]
    assert recent[0]["title"] == "Data Engineer"
    assert recent[0]["company_name"] == "Harbor"


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
    assert client.get(f"/api/jobs/{job['id']}", headers=_auth()).status_code == 404
    listed = client.get("/api/jobs", headers=_auth())
    assert all(row["id"] != job["id"] for row in listed.json())

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


def test_dismiss_jobs_bulk(client: TestClient) -> None:
    keep = client.post(
        "/api/jobs",
        headers=_auth(),
        json={"title": "Keep me", "description": "Data pipelines"},
    ).json()
    drop_a = client.post(
        "/api/jobs",
        headers=_auth(),
        json={"title": "Sales A", "description": "Quota"},
    ).json()
    drop_b = client.post(
        "/api/jobs",
        headers=_auth(),
        json={"title": "Sales B", "description": "Quota"},
    ).json()
    response = client.post(
        "/api/jobs/not-related",
        headers=_auth(),
        json={"job_ids": [drop_a["id"], drop_b["id"], "00000000-0000-0000-0000-000000000000"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body["dismissed"]) == {drop_a["id"], drop_b["id"]}
    assert body["missing"] == ["00000000-0000-0000-0000-000000000000"]
    listed = client.get("/api/jobs", headers=_auth()).json()
    ids = {row["id"] for row in listed}
    assert keep["id"] in ids
    assert drop_a["id"] not in ids
    assert drop_b["id"] not in ids


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


def test_create_post_and_progress(client: TestClient) -> None:
    created = client.post(
        "/api/posts",
        headers=_auth(),
        json={
            "title": "How I track remote work",
            "summary": "Pipeline notes",
            "body": "Jobs, prospects, and posts.",
            "tags": ["career", "freelance"],
            "channels": ["web", "linkedin"],
            "web_url": "https://tyorus.com/notes/remote-work",
            "linkedin_url": "https://www.linkedin.com/feed/update/urn:li:activity:1",
            "cover_url": "https://tyorus.com/cover.png",
            "media_json": [
                {
                    "kind": "image",
                    "url": "https://tyorus.com/cover.png",
                    "caption": "Hero",
                }
            ],
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "idea"
    assert body["channels"] == ["web", "linkedin"]
    assert body["web_url"].endswith("/remote-work")
    assert body["media_json"][0]["kind"] == "image"
    post_id = body["id"]

    patched = client.patch(
        f"/api/posts/{post_id}",
        headers=_auth(),
        json={"canonical_url": "https://tyorus.com/notes/remote-work"},
    )
    assert patched.status_code == 200
    assert patched.json()["canonical_url"].endswith("/remote-work")

    progress = client.post(
        f"/api/posts/{post_id}/progress",
        headers=_auth(),
        json={"status": "published", "note": "Live on web and LinkedIn"},
    )
    assert progress.status_code == 201
    assert progress.json()["status"] == "published"
    fetched = client.get(f"/api/posts/{post_id}", headers=_auth())
    assert fetched.json()["status"] == "published"
    assert fetched.json()["published_at"]
    listed = client.get("/api/posts?channel=linkedin", headers=_auth())
    assert listed.json()[0]["title"] == "How I track remote work"
    board = client.get("/api/dashboard", headers=_auth())
    assert board.json()["posts_total"] == 1
    recent = board.json()["recent_progress"]
    assert recent[0]["title"] == "How I track remote work"
    assert recent[0]["entity_type"] == "post"


def test_invalid_post_status(client: TestClient) -> None:
    created = client.post(
        "/api/posts",
        headers=_auth(),
        json={"title": "Draft note"},
    )
    post_id = created.json()["id"]
    response = client.post(
        f"/api/posts/{post_id}/progress",
        headers=_auth(),
        json={"status": "nope"},
    )
    assert response.status_code == 400
    missing = client.get(
        "/api/posts/00000000-0000-0000-0000-000000000000",
        headers=_auth(),
    )
    assert missing.status_code == 404


