"""Vercel Python entrypoint for the FastAPI tracker API."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from jobintel.api.app import app  # noqa: E402

__all__ = ["app"]
