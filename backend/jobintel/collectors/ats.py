"""Greenhouse and Lever public board JSON collectors."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx

from jobintel.collectors.http import USER_AGENT, get_json
from jobintel.collectors.normalize import looks_remote
from jobintel.models import CollectedJob, RemoteType
from jobintel.text import clean_description


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        raw = int(value)
        if raw > 10_000_000_000:
            raw //= 1000
        try:
            return datetime.fromtimestamp(raw, tz=UTC)
        except (ValueError, OSError):
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


def fetch_greenhouse(board_token: str, *, limit: int = 80) -> list[CollectedJob]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
    try:
        payload = get_json(url)
    except httpx.HTTPError:
        return []
    rows = payload.get("jobs") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return []
    jobs: list[CollectedJob] = []
    for item in rows:
        if not isinstance(item, dict) or not item.get("title"):
            continue
        location_obj = item.get("location") or {}
        location = None
        if isinstance(location_obj, dict):
            location = location_obj.get("name")
        location = str(location) if location else None
        if location and not looks_remote(location):
            continue
        abs_url = str(item.get("absolute_url") or "").strip()
        if not abs_url:
            continue
        departments = item.get("departments") or []
        department = None
        if isinstance(departments, list) and departments:
            first = departments[0]
            if isinstance(first, dict):
                department = str(first.get("name") or "") or None
            else:
                department = str(first)
        jobs.append(
            CollectedJob(
                title=str(item["title"]).strip(),
                company_name=board_token,
                url=abs_url,
                description=clean_description(str(item.get("content") or "")) or str(item["title"]),
                location=location,
                remote_type=(
                    RemoteType.REMOTE if looks_remote(location, True) else RemoteType.UNKNOWN
                ),
                source="greenhouse",
                source_job_id=str(item.get("id") or "") or None,
                posted_at=_parse_dt(item.get("first_published") or item.get("updated_at")),
                department=department,
                metadata_json={
                    "updated_at": item.get("updated_at"),
                    "first_published": item.get("first_published"),
                },
            )
        )
        if len(jobs) >= limit:
            break
    return jobs


def fetch_lever(company: str, *, limit: int = 80) -> list[CollectedJob]:
    url = f"https://api.lever.co/v0/postings/{company}?mode=json"
    try:
        with httpx.Client(
            timeout=30.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True
        ) as client:
            response = client.get(url)
            if response.status_code >= 400:
                return []
            rows = response.json()
    except httpx.HTTPError:
        return []
    if not isinstance(rows, list):
        return []
    jobs: list[CollectedJob] = []
    for item in rows:
        if not isinstance(item, dict) or not item.get("text"):
            continue
        categories = item.get("categories") or {}
        location = None
        if isinstance(categories, dict):
            location = categories.get("location")
        location = str(location) if location else None
        commitment = None
        team = company
        if isinstance(categories, dict):
            commitment = categories.get("commitment")
            team = str(categories.get("team") or company)
            workplace = str(commitment or categories.get("workType") or "")
        else:
            workplace = ""
        if location and not looks_remote(location) and "remote" not in workplace.lower():
            continue
        hosted = str(item.get("hostedUrl") or item.get("applyUrl") or "").strip()
        if not hosted:
            continue
        apply_url = str(item.get("applyUrl") or "").strip() or None
        description = clean_description(
            str(item.get("descriptionPlain") or item.get("description") or "")
        )
        jobs.append(
            CollectedJob(
                title=str(item["text"]).strip(),
                company_name=team,
                url=hosted,
                apply_url=apply_url if apply_url and apply_url != hosted else None,
                description=description or str(item["text"]),
                location=location,
                remote_type=RemoteType.REMOTE,
                source="lever",
                source_job_id=str(item.get("id") or "") or None,
                posted_at=_parse_dt(item.get("createdAt")),
                employment_type=str(commitment) if commitment else None,
                department=team if team != company else None,
                metadata_json={
                    "categories": categories if isinstance(categories, dict) else {},
                },
            )
        )
        if len(jobs) >= limit:
            break
    return jobs
