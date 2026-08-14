"""Normalize and filter collected jobs."""

from __future__ import annotations

import hashlib
import re
from html.parser import HTMLParser

from jobintel.models import CollectedJob


class _HTMLStripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        self._chunks.append(data)

    def text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self._chunks)).strip()


def strip_html(value: str | None) -> str:
    if not value:
        return ""
    stripper = _HTMLStripper()
    try:
        stripper.feed(value)
        stripper.close()
    except Exception:
        return re.sub(r"<[^>]+>", " ", value)
    return stripper.text() or re.sub(r"<[^>]+>", " ", value)


def job_content_hash(*, title: str, company: str, description: str) -> str:
    blob = "|".join(
        [
            title.strip().lower(),
            company.strip().lower(),
            " ".join(strip_html(description).lower().split())[:4000],
        ]
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def matches_keywords(job: CollectedJob, keywords: list[str]) -> bool:
    if not keywords:
        return True
    haystack = " ".join(
        [
            job.title,
            job.company_name,
            job.location or "",
            strip_html(job.description)[:4000],
        ]
    ).lower()
    return any(keyword in haystack for keyword in keywords)


def looks_remote(location: str | None, remote_flag: bool | None = None) -> bool:
    if remote_flag is True:
        return True
    if remote_flag is False:
        text = (location or "").lower()
        return "remote" in text
    if not location:
        return True
    text = location.lower()
    if any(token in text for token in ("onsite", "on-site", "office only")):
        return "remote" in text
    return True
