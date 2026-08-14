"""Tests for tracker collectors and keyword filtering."""

from __future__ import annotations

from jobintel.collectors.normalize import job_content_hash, matches_keywords, strip_html
from jobintel.collectors.rss import parse_feed
from jobintel.models import CollectedJob, RemoteType


def test_strip_html_and_hash_stable() -> None:
    text = strip_html("<p>Python <b>ETL</b> pipelines</p>")
    assert "Python ETL pipelines" == text
    a = job_content_hash(title="DE", company="Acme", description="<p>Hello</p>")
    b = job_content_hash(title="DE", company="Acme", description="Hello")
    assert a == b
    c = job_content_hash(title="DE", company="Other", description="Hello")
    assert a != c


def test_keyword_filter() -> None:
    job = CollectedJob(
        title="Senior Data Engineer",
        company_name="Acme",
        url="https://example.com/jobs/1",
        description="Build Python ETL pipelines",
        remote_type=RemoteType.REMOTE,
        source="remoteok",
    )
    assert matches_keywords(job, ["python", "fastapi"])
    assert not matches_keywords(job, ["golang", "kubernetes"])
    assert matches_keywords(job, [])


def test_parse_rss_items() -> None:
    xml = """<?xml version="1.0"?>
    <rss version="2.0">
      <channel>
        <item>
          <title>Harbor Labs: Python Data Engineer</title>
          <link>https://weworkremotely.com/jobs/1</link>
          <description>Remote pandas work</description>
          <pubDate>Tue, 12 Aug 2026 10:00:00 +0000</pubDate>
        </item>
      </channel>
    </rss>
    """
    items = parse_feed(xml)
    assert len(items) == 1
    assert items[0]["title"].startswith("Harbor Labs")
    assert "weworkremotely.com" in items[0]["link"]
