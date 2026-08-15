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


# Generic tokens that appear in almost any posting or RemoteOK category tags.
_WEAK_KEYWORDS = {
    "sql",
    "pipeline",
    "ocean",
    "analytics",
    "ops",
    "automation",
}

_UNRELATED_TITLE = re.compile(
    r"\b("
    r"painter|barber|lifeguard|handyman|electrician|plumber|carpenter|"
    r"driver|cook|chef|cashier|waiter|nurse|caregiver|housekeep|"
    r"beekeeper|labourer|laborer|estimator|payroll specialist"
    r")\b",
    re.I,
)

_SPAM_TITLE = re.compile(
    r"(how apply|apply today|12th pass|talk us here|expression of interest|"
    r"can.?t find the job)",
    re.I,
)

_TAGS_LINE = re.compile(r"(?im)^tags:\s*.*$")


def _contains_keyword(text: str, keyword: str) -> bool:
    pattern = r"(?<![a-z0-9])" + re.escape(keyword) + r"(?![a-z0-9])"
    return re.search(pattern, text, flags=re.I) is not None


def _is_strong_keyword(keyword: str) -> bool:
    return keyword not in _WEAK_KEYWORDS


def matches_keywords(job: CollectedJob, keywords: list[str]) -> bool:
    if not keywords:
        return True
    title = job.title or ""
    if _UNRELATED_TITLE.search(title) or _SPAM_TITLE.search(title):
        return False
    description = _TAGS_LINE.sub(" ", strip_html(job.description)[:4000])
    title_hits = [kw for kw in keywords if _contains_keyword(title, kw)]
    if title_hits:
        return True
    return any(
        _is_strong_keyword(kw) and _contains_keyword(description, kw) for kw in keywords
    )


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
