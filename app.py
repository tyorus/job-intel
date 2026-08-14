"""Root FastAPI entrypoint for Vercel (supported filename)."""

from backend.jobintel.api.app import app

__all__ = ["app"]
