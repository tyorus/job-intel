"""Vercel Python entrypoint for the FastAPI tracker API."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"

# Ensure local package is importable when Vercel has not installed the project wheel.
for path in (_BACKEND, _ROOT):
    text = str(path)
    if path.is_dir() and text not in sys.path:
        sys.path.insert(0, text)

try:
    from jobintel.api.app import app
except Exception as exc:  # noqa: BLE001 — surface import failures in /api/health
    from fastapi import FastAPI

    app = FastAPI(title="Job Intelligence Tracker (boot error)")
    _boot_error = f"{type(exc).__name__}: {exc}"

    @app.get("/api/health")
    def health_boot_error() -> dict[str, str]:
        return {"status": "error", "detail": _boot_error}

    @app.api_route("/api/{full_path:path}", methods=["GET", "POST", "PATCH", "PUT", "DELETE"])
    def api_boot_error(full_path: str) -> dict[str, str]:
        return {"status": "error", "detail": _boot_error}


__all__ = ["app"]
