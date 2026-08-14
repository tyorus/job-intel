"""HTTP helpers for public job APIs."""

from __future__ import annotations

from typing import Any

import httpx

USER_AGENT = "jobintel-tracker/0.1 (+https://tyorus.com; personal job tracker)"


def get_json(url: str, *, timeout: float = 30.0) -> Any:
    headers = {"User-Agent": USER_AGENT}
    with httpx.Client(timeout=timeout, headers=headers, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.json()


def get_text(url: str, *, timeout: float = 30.0) -> str:
    headers = {"User-Agent": USER_AGENT}
    with httpx.Client(timeout=timeout, headers=headers, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text
