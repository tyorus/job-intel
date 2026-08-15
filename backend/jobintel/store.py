"""Supabase persistence for jobs, prospects, and progress events."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from jobintel.collectors.normalize import job_content_hash
from jobintel.db import get_supabase_client
from jobintel.models import (
    ApplicationStatus,
    CollectedJob,
    Job,
    JobRead,
    JobStatus,
    ProgressEntityType,
    ProgressEvent,
    Prospect,
    ProspectStatus,
)
from jobintel.text import clean_description


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _dump(payload: dict[str, Any]) -> dict[str, Any]:
    """Drop Nones so Postgres defaults apply."""
    return {key: value for key, value in payload.items() if value is not None}


class Store:
    def __init__(self, client: Any | None = None) -> None:
        self.client = client or get_supabase_client()

    # --- companies ---------------------------------------------------------

    def ensure_company(self, name: str) -> UUID | None:
        cleaned = name.strip()
        if not cleaned:
            return None
        existing = (
            self.client.table("companies")
            .select("id")
            .eq("name", cleaned)
            .limit(1)
            .execute()
        )
        if existing.data:
            return UUID(str(existing.data[0]["id"]))
        inserted = (
            self.client.table("companies")
            .insert({"name": cleaned})
            .execute()
        )
        if inserted.data:
            return UUID(str(inserted.data[0]["id"]))
        return None

    def _company_map(self, company_ids: list[str]) -> dict[str, str]:
        ids = [cid for cid in company_ids if cid]
        if not ids:
            return {}
        result = (
            self.client.table("companies")
            .select("id, name")
            .in_("id", ids)
            .execute()
        )
        return {str(row["id"]): row["name"] for row in (result.data or [])}

    def _to_job_read(self, row: dict[str, Any], company_name: str | None) -> JobRead:
        data = dict(row)
        tags = data.get("tags")
        if isinstance(tags, str):
            try:
                data["tags"] = json.loads(tags)
            except json.JSONDecodeError:
                data["tags"] = []
        meta = data.get("metadata_json")
        if isinstance(meta, str):
            try:
                data["metadata_json"] = json.loads(meta)
            except json.JSONDecodeError:
                data["metadata_json"] = {}
        if isinstance(data.get("description"), str):
            data["description"] = clean_description(data["description"])
        return JobRead.model_validate({**data, "company_name": company_name})

    # --- jobs --------------------------------------------------------------

    def list_jobs(
        self,
        *,
        status: str | None = None,
        source: str | None = None,
        q: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[JobRead]:
        query = self.client.table("jobs").select("*")
        if status:
            query = query.eq("status", status)
        if source:
            query = query.eq("source", source)
        if q:
            like = f"%{q}%"
            query = query.or_(f"title.ilike.{like},description.ilike.{like}")
        result = (
            query.order("discovered_at", desc=True).range(offset, offset + limit - 1).execute()
        )
        rows = result.data or []
        names = self._company_map([str(r.get("company_id") or "") for r in rows])
        return [
            self._to_job_read(row, names.get(str(row.get("company_id") or "")))
            for row in rows
        ]

    def get_job(self, job_id: UUID) -> JobRead | None:
        result = (
            self.client.table("jobs").select("*").eq("id", str(job_id)).limit(1).execute()
        )
        if not result.data:
            return None
        row = result.data[0]
        names = self._company_map([str(row.get("company_id") or "")])
        return self._to_job_read(row, names.get(str(row.get("company_id") or "")))

    def create_job(self, job: Job, company_name: str | None = None) -> JobRead:
        company_id = job.company_id
        if company_name and not company_id:
            company_id = self.ensure_company(company_name)
        payload = _dump(
            job.model_dump(mode="json", exclude={"id", "created_at", "updated_at", "discovered_at"})
        )
        if payload.get("url") == "":
            payload.pop("url", None)
        if company_id:
            payload["company_id"] = str(company_id)
        if isinstance(payload.get("description"), str):
            payload["description"] = clean_description(payload["description"])
        if not payload.get("content_hash"):
            payload["content_hash"] = job_content_hash(
                title=job.title,
                company=company_name or "",
                description=job.description,
            )
        result = self.client.table("jobs").insert(payload).execute()
        row = result.data[0]
        return self._to_job_read(row, company_name)

    def update_job(self, job_id: UUID, fields: dict[str, Any]) -> JobRead:
        if not self.get_job(job_id):
            raise KeyError(f"job not found: {job_id}")
        payload = _dump(fields)
        if not payload:
            found = self.get_job(job_id)
            assert found is not None
            return found
        result = self.client.table("jobs").update(payload).eq("id", str(job_id)).execute()
        row = result.data[0]
        names = self._company_map([str(row.get("company_id") or "")])
        return self._to_job_read(row, names.get(str(row.get("company_id") or "")))

    def delete_job(self, job_id: UUID) -> None:
        if not self.get_job(job_id):
            raise KeyError(f"job not found: {job_id}")
        job_key = str(job_id)
        self.client.table("applications").delete().eq("job_id", job_key).execute()
        (
            self.client.table("progress_events")
            .delete()
            .eq("entity_type", "job")
            .eq("entity_id", job_key)
            .execute()
        )
        self.client.table("jobs").delete().eq("id", job_key).execute()

    def existing_job_keys(self) -> tuple[set[str], set[str]]:
        urls: set[str] = set()
        hashes: set[str] = set()
        start = 0
        page = 1000
        while True:
            result = (
                self.client.table("jobs")
                .select("url, content_hash")
                .range(start, start + page - 1)
                .execute()
            )
            rows = result.data or []
            for row in rows:
                if row.get("url"):
                    urls.add(str(row["url"]))
                if row.get("content_hash"):
                    hashes.add(str(row["content_hash"]))
            if len(rows) < page:
                break
            start += page
        return urls, hashes

    def insert_collected_jobs(self, collected: list[CollectedJob]) -> dict[str, int]:
        urls, hashes = self.existing_job_keys()
        inserted = 0
        skipped = 0
        company_cache: dict[str, UUID | None] = {}

        for item in collected:
            digest = job_content_hash(
                title=item.title,
                company=item.company_name,
                description=item.description,
            )
            if item.url in urls or digest in hashes:
                skipped += 1
                continue
            company_id = company_cache.get(item.company_name)
            if item.company_name not in company_cache:
                company_id = self.ensure_company(item.company_name)
                company_cache[item.company_name] = company_id
            payload = _dump(
                {
                    "company_id": str(company_id) if company_id else None,
                    "title": item.title,
                    "location": item.location,
                    "country": item.country,
                    "remote_type": item.remote_type.value,
                    "source": item.source,
                    "source_job_id": item.source_job_id,
                    "url": item.url,
                    "apply_url": item.apply_url,
                    "description": item.description,
                    "posted_at": item.posted_at.isoformat() if item.posted_at else None,
                    "deadline_at": item.deadline_at.isoformat() if item.deadline_at else None,
                    "salary_text": item.salary_text,
                    "employment_type": item.employment_type,
                    "department": item.department,
                    "seniority": item.seniority,
                    "tags": item.tags,
                    "metadata_json": item.metadata_json,
                    "status": JobStatus.NEW.value,
                    "content_hash": digest,
                }
            )
            try:
                self.client.table("jobs").insert(payload).execute()
            except Exception:
                skipped += 1
                continue
            urls.add(item.url)
            hashes.add(digest)
            inserted += 1
        return {"inserted": inserted, "skipped": skipped, "seen": len(collected)}

    def submit_job_progress(
        self, job_id: UUID, status: JobStatus, note: str | None = None
    ) -> ProgressEvent:
        if not self.get_job(job_id):
            raise KeyError(f"job not found: {job_id}")
        self.client.table("jobs").update({"status": status.value}).eq(
            "id", str(job_id)
        ).execute()
        app_status = ApplicationStatus(status.value)
        existing = (
            self.client.table("applications")
            .select("id")
            .eq("job_id", str(job_id))
            .limit(1)
            .execute()
        )
        app_payload: dict[str, Any] = {"status": app_status.value, "notes": note}
        if status == JobStatus.APPLIED:
            app_payload["applied_at"] = _now()
        if existing.data:
            self.client.table("applications").update(_dump(app_payload)).eq(
                "id", existing.data[0]["id"]
            ).execute()
        else:
            self.client.table("applications").insert(
                _dump({"job_id": str(job_id), **app_payload})
            ).execute()
        return self._insert_progress(ProgressEntityType.JOB, job_id, status.value, note)

    # --- prospects ---------------------------------------------------------

    def list_prospects(
        self,
        *,
        status: str | None = None,
        package: str | None = None,
        q: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Prospect]:
        query = self.client.table("prospects").select("*")
        if status:
            query = query.eq("status", status)
        if package:
            query = query.eq("package", package)
        if q:
            like = f"%{q}%"
            query = query.or_(f"name.ilike.{like},company.ilike.{like},notes.ilike.{like}")
        result = (
            query.order("updated_at", desc=True).range(offset, offset + limit - 1).execute()
        )
        return [Prospect.model_validate(row) for row in (result.data or [])]

    def get_prospect(self, prospect_id: UUID) -> Prospect | None:
        result = (
            self.client.table("prospects")
            .select("*")
            .eq("id", str(prospect_id))
            .limit(1)
            .execute()
        )
        if not result.data:
            return None
        return Prospect.model_validate(result.data[0])

    def create_prospect(self, prospect: Prospect) -> Prospect:
        payload = _dump(
            prospect.model_dump(mode="json", exclude={"id", "created_at", "updated_at"})
        )
        result = self.client.table("prospects").insert(payload).execute()
        created = Prospect.model_validate(result.data[0])
        self._insert_progress(
            ProgressEntityType.PROSPECT,
            created.id,  # type: ignore[arg-type]
            created.status.value,
            prospect.notes,
        )
        return created

    def update_prospect(self, prospect_id: UUID, fields: dict[str, Any]) -> Prospect:
        if not self.get_prospect(prospect_id):
            raise KeyError(f"prospect not found: {prospect_id}")
        payload = _dump(fields)
        if not payload:
            found = self.get_prospect(prospect_id)
            assert found is not None
            return found
        result = (
            self.client.table("prospects")
            .update(payload)
            .eq("id", str(prospect_id))
            .execute()
        )
        return Prospect.model_validate(result.data[0])

    def submit_prospect_progress(
        self, prospect_id: UUID, status: ProspectStatus, note: str | None = None
    ) -> ProgressEvent:
        if not self.get_prospect(prospect_id):
            raise KeyError(f"prospect not found: {prospect_id}")
        update: dict[str, Any] = {"status": status.value}
        if note:
            update["notes"] = note
        if status == ProspectStatus.CONTACTED:
            update["date_contacted"] = datetime.now(UTC).date().isoformat()
        if status == ProspectStatus.PROPOSAL:
            update["proposal_sent"] = True
        self.client.table("prospects").update(update).eq("id", str(prospect_id)).execute()
        return self._insert_progress(
            ProgressEntityType.PROSPECT, prospect_id, status.value, note
        )

    # --- progress / dashboard ----------------------------------------------

    def list_progress(
        self,
        *,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        since: str | None = None,
        limit: int = 50,
    ) -> list[ProgressEvent]:
        query = self.client.table("progress_events").select("*")
        if entity_type:
            query = query.eq("entity_type", entity_type)
        if entity_id:
            query = query.eq("entity_id", str(entity_id))
        if since:
            query = query.gte("created_at", since)
        result = query.order("created_at", desc=True).limit(limit).execute()
        return [ProgressEvent.model_validate(row) for row in (result.data or [])]

    def dashboard(self) -> dict[str, Any]:
        jobs = self.client.table("jobs").select("status").execute().data or []
        prospects = self.client.table("prospects").select("status").execute().data or []
        job_counts: dict[str, int] = {}
        prospect_counts: dict[str, int] = {}
        for row in jobs:
            key = str(row.get("status") or "unknown")
            job_counts[key] = job_counts.get(key, 0) + 1
        for row in prospects:
            key = str(row.get("status") or "unknown")
            prospect_counts[key] = prospect_counts.get(key, 0) + 1
        recent = self.list_progress(limit=20)
        return {
            "jobs_total": len(jobs),
            "prospects_total": len(prospects),
            "jobs_by_status": job_counts,
            "prospects_by_status": prospect_counts,
            "recent_progress": [event.model_dump(mode="json") for event in recent],
        }

    def _insert_progress(
        self,
        entity_type: ProgressEntityType,
        entity_id: UUID,
        status: str,
        note: str | None,
    ) -> ProgressEvent:
        result = (
            self.client.table("progress_events")
            .insert(
                _dump(
                    {
                        "entity_type": entity_type.value,
                        "entity_id": str(entity_id),
                        "status": status,
                        "note": note,
                    }
                )
            )
            .execute()
        )
        return ProgressEvent.model_validate(result.data[0])
