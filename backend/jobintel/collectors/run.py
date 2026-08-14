"""Run all public collectors, filter, and persist new jobs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from jobintel.collectors.arbeitnow import fetch_arbeitnow
from jobintel.collectors.ats import fetch_greenhouse, fetch_lever
from jobintel.collectors.normalize import matches_keywords
from jobintel.collectors.remoteok import fetch_remoteok
from jobintel.collectors.rss import fetch_rss
from jobintel.config import Settings, get_settings
from jobintel.models import CollectedJob

ALL_SOURCES = ("remoteok", "arbeitnow", "greenhouse", "lever", "rss")


def load_boards(path: Path | None = None, settings: Settings | None = None) -> dict[str, Any]:
    cfg = settings or get_settings()
    boards_path = path or cfg.collectors_config_path
    if not boards_path.is_file():
        return {"greenhouse": [], "lever": [], "rss": []}
    raw = yaml.safe_load(boards_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return {"greenhouse": [], "lever": [], "rss": []}
    return {
        "greenhouse": list(raw.get("greenhouse") or []),
        "lever": list(raw.get("lever") or []),
        "rss": list(raw.get("rss") or []),
    }


def collect_jobs(
    *,
    sources: list[str] | None = None,
    settings: Settings | None = None,
    boards: dict[str, Any] | None = None,
) -> list[CollectedJob]:
    cfg = settings or get_settings()
    wanted = set(sources or ALL_SOURCES)
    board_cfg = boards if boards is not None else load_boards(settings=cfg)
    limit = cfg.scrape_max_per_source
    collected: list[CollectedJob] = []

    if "remoteok" in wanted:
        collected.extend(fetch_remoteok(limit=limit))
    if "arbeitnow" in wanted:
        collected.extend(fetch_arbeitnow(limit=limit))
    if "greenhouse" in wanted:
        for token in board_cfg.get("greenhouse") or []:
            collected.extend(fetch_greenhouse(str(token), limit=limit))
    if "lever" in wanted:
        for company in board_cfg.get("lever") or []:
            collected.extend(fetch_lever(str(company), limit=limit))
    if "rss" in wanted:
        for feed in board_cfg.get("rss") or []:
            collected.extend(fetch_rss(str(feed), limit=limit))

    keywords = cfg.keyword_list
    filtered = [job for job in collected if matches_keywords(job, keywords)]
    # Dedup within this run by URL
    seen: set[str] = set()
    unique: list[CollectedJob] = []
    for job in filtered:
        if job.url in seen:
            continue
        seen.add(job.url)
        unique.append(job)
    return unique


def scrape_to_store(
    store: Any,
    *,
    sources: list[str] | None = None,
    settings: Settings | None = None,
) -> dict[str, int]:
    jobs = collect_jobs(sources=sources, settings=settings)
    result = store.insert_collected_jobs(jobs)
    result["matched"] = len(jobs)
    return result
