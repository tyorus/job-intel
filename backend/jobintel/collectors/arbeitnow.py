"""Arbeitnow public job-board API collector."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from jobintel.collectors.http import get_json
from jobintel.collectors.normalize import looks_remote, strip_html
from jobintel.models import CollectedJob, RemoteType


def _posted_at(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed
    except ValueError:
        return None


def fetch_arbeitnow(*, limit: int = 80) -> list[CollectedJob]:
    payload = get_json("https://www.arbeitnow.com/api/job-board-api")
    rows = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return []
    jobs: list[CollectedJob] = []
    for item in rows:
        if not isinstance(item, dict) or not item.get("title"):
            continue
        remote = bool(item.get("remote"))
        location = str(item.get("location") or "") or None
        if not looks_remote(location, remote):
            continue
        url = str(item.get("url") or "").strip()
        if not url:
            continue
        tags_raw = item.get("tags") or []
        if isinstance(tags_raw, list):
            tags = [str(t).strip() for t in tags_raw if str(t).strip()]
        else:
            tags = []
        job_types = item.get("job_types") or []
        employment = None
        if isinstance(job_types, list) and job_types:
            employment = ", ".join(str(t) for t in job_types)
        jobs.append(
            CollectedJob(
                title=str(item["title"]).strip(),
                company_name=str(item.get("company_name") or "Unknown").strip() or "Unknown",
                url=url,
                description=strip_html(str(item.get("description") or "")) or str(item["title"]),
                location=location or ("Remote" if remote else None),
                remote_type=(
                    RemoteType.REMOTE
                    if remote or looks_remote(location, True)
                    else RemoteType.UNKNOWN
                ),
                source="arbeitnow",
                source_job_id=str(item.get("slug") or "") or None,
                posted_at=_posted_at(item.get("created_at")),
                employment_type=employment,
                tags=tags,
                metadata_json={
                    k: item.get(k)
                    for k in ("slug", "url")
                    if item.get(k) is not None
                },
            )
        )
        if len(jobs) >= limit:
            break
    return jobs
