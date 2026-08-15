"""Tests for scraped job description cleaning."""

from __future__ import annotations

from jobintel.text import clean_description


def test_html_lists_and_headings_become_markdown() -> None:
    html = """
    <div>
      <h2>Responsibilities</h2>
      <ul>
        <li>Build Python ETL pipelines</li>
        <li>Own Airflow DAGs</li>
      </ul>
      <h2>Requirements</h2>
      <p>Five years of experience. Strong SQL skills. Cloud fluency.</p>
    </div>
    """
    text = clean_description(html)
    assert "## Responsibilities" in text
    assert "- Build Python ETL pipelines" in text
    assert "- Own Airflow DAGs" in text
    assert "## Requirements" in text
    assert "- Five years of experience" in text
    assert "<li>" not in text


def test_flattened_prose_gets_section_breaks() -> None:
    raw = (
        "We are looking for a hands-on PM. "
        "Responsibilities Turn vague ideas into requirements. "
        "Own backlog refinement. Plan sprints and releases. "
        "Requirements Strong software experience. Fintech preferred. "
        "Excellent written communication."
    )
    text = clean_description(raw)
    assert "## Responsibilities" in text
    assert "## Requirements" in text
    assert "- Turn vague ideas into requirements" in text
    assert text.count("##") >= 2


def test_wwr_chrome_is_stripped() -> None:
    raw = (
        "Headquarters: ignitionit.com URL: https://ignitionit.com "
        "APPLY HERE: https://example.com/apply Fully Remote role. "
        "About the role You will help clients when something is broken. "
        "We have been in business for almost 30 years."
    )
    text = clean_description(raw)
    assert "Headquarters:" not in text
    assert "APPLY HERE:" not in text
    assert "https://ignitionit.com" not in text
    assert "## About the role" in text


def test_clean_description_is_idempotent() -> None:
    html = "<h2>Requirements</h2><ul><li>Python</li><li>SQL</li></ul>"
    once = clean_description(html)
    twice = clean_description(once)
    assert once == twice
