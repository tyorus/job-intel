"""RSS / Atom collectors (We Work Remotely and custom feeds)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx

from jobintel.collectors.http import get_text
from jobintel.models import CollectedJob, RemoteType
from jobintel.text import clean_description

ATOM = "{http://www.w3.org/2005/Atom}"


def _child_text(node: ET.Element, tag: str) -> str:
    child = node.find(tag)
    if child is None or child.text is None:
        return ""
    return child.text.strip()


def parse_feed(xml_text: str) -> list[dict[str, str]]:
    root = ET.fromstring(xml_text)
    items: list[dict[str, str]] = []
    for item in root.findall(".//item"):
        items.append(
            {
                "title": _child_text(item, "title"),
                "link": _child_text(item, "link"),
                "description": _child_text(item, "description")
                or _child_text(item, "{http://purl.org/rss/1.0/modules/content/}encoded"),
                "pubDate": _child_text(item, "pubDate"),
            }
        )
    if items:
        return items
    for entry in root.findall(f".//{ATOM}entry"):
        link = ""
        link_el = entry.find(f"{ATOM}link")
        if link_el is not None:
            link = (link_el.get("href") or "").strip() or _child_text(entry, f"{ATOM}link")
        items.append(
            {
                "title": _child_text(entry, f"{ATOM}title"),
                "link": link,
                "description": (
                    _child_text(entry, f"{ATOM}summary")
                    or _child_text(entry, f"{ATOM}content")
                ),
                "pubDate": (
                    _child_text(entry, f"{ATOM}updated")
                    or _child_text(entry, f"{ATOM}published")
                ),
            }
        )
    return items


def _posted_at(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed
    except (TypeError, ValueError):
        pass
    try:
        text = value[:-1] + "+00:00" if value.endswith("Z") else value
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed
    except ValueError:
        return None


def _split_wwr_title(title: str) -> tuple[str, str]:
    """WWR titles are often 'Company: Role'."""
    if ":" in title:
        company, role = title.split(":", 1)
        return role.strip() or title, company.strip() or "Unknown"
    return title.strip(), "Unknown"


def fetch_rss(feed_url: str, *, limit: int = 80, source: str = "rss") -> list[CollectedJob]:
    try:
        xml_text = get_text(feed_url)
    except httpx.HTTPError:
        return []
    jobs: list[CollectedJob] = []
    for item in parse_feed(xml_text):
        title_raw = item.get("title") or ""
        url = (item.get("link") or "").strip()
        if not title_raw or not url:
            continue
        role, company = _split_wwr_title(title_raw)
        if "weworkremotely.com" in feed_url:
            source_name = "weworkremotely"
        else:
            source_name = source
        jobs.append(
            CollectedJob(
                title=role,
                company_name=company,
                url=url,
                description=clean_description(item.get("description") or "") or role,
                location="Remote",
                remote_type=RemoteType.REMOTE,
                source=source_name,
                source_job_id=url,
                posted_at=_posted_at(item.get("pubDate") or ""),
            )
        )
        if len(jobs) >= limit:
            break
    return jobs
