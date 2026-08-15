"""RemoteOK public API collector. https://remoteok.com/api"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from jobintel.collectors.http import get_json
from jobintel.models import CollectedJob, RemoteType
from jobintel.text import clean_description


def _posted_at(item: dict[str, Any]) -> datetime | None:
    epoch = item.get("epoch")
    if epoch is None:
        return None
    try:
        return datetime.fromtimestamp(int(epoch), tz=UTC)
    except (TypeError, ValueError, OSError):
        return None


def _tags(item: dict[str, Any]) -> list[str]:
    tags = item.get("tags") or []
    if not isinstance(tags, list):
        return []
    return [str(tag).strip() for tag in tags if str(tag).strip()]


def fetch_remoteok(*, limit: int = 80) -> list[CollectedJob]:
    payload = get_json("https://remoteok.com/api")
    if not isinstance(payload, list):
        return []
    jobs: list[CollectedJob] = []
    for item in payload:
        if not isinstance(item, dict) or not item.get("position"):
            continue
        job_id = str(item.get("id") or item.get("slug") or "")
        url = str(item.get("url") or item.get("apply_url") or "").strip()
        if not url:
            continue
        tags = _tags(item)
        description = clean_description(str(item.get("description") or ""))
        salary = item.get("salary") or item.get("salary_min") or item.get("salary_max")
        salary_text = str(salary).strip() if salary not in (None, "") else None
        apply_url = str(item.get("apply_url") or "").strip() or None
        jobs.append(
            CollectedJob(
                title=str(item["position"]).strip(),
                company_name=str(item.get("company") or "Unknown").strip() or "Unknown",
                url=url,
                apply_url=apply_url if apply_url != url else None,
                description=description or str(item["position"]),
                location=str(item.get("location") or "Remote") or "Remote",
                country=None,
                remote_type=RemoteType.REMOTE,
                source="remoteok",
                source_job_id=job_id or None,
                posted_at=_posted_at(item),
                salary_text=salary_text,
                tags=tags,
                metadata_json={
                    k: item.get(k)
                    for k in ("slug", "company_logo", "date")
                    if item.get(k) is not None
                },
            )
        )
        if len(jobs) >= limit:
            break
    return jobs
