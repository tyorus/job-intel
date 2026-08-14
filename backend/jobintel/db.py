"""Thin Supabase client helpers (no live writes required for Milestone 1)."""

from __future__ import annotations

from typing import Any

from jobintel.config import Settings, get_settings


class DatabaseNotConfiguredError(RuntimeError):
    """Raised when Supabase credentials are missing."""


def get_supabase_client(settings: Settings | None = None) -> Any:
    """
    Return a Supabase client using the service role key.

    Milestone 1 only validates configuration wiring; callers that need a live
    client must set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.
    """
    cfg = settings or get_settings()
    if not cfg.supabase_url or not cfg.supabase_service_role_key:
        raise DatabaseNotConfiguredError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set to create a client."
        )
    from supabase import create_client

    return create_client(cfg.supabase_url, cfg.supabase_service_role_key)


def is_configured(settings: Settings | None = None) -> bool:
    cfg = settings or get_settings()
    return bool(cfg.supabase_url and cfg.supabase_service_role_key)


def get_store(settings: Settings | None = None) -> Any:
    """Supabase when configured; otherwise local SQLite so the tracker can run offline."""
    cfg = settings or get_settings()
    if is_configured(cfg):
        from jobintel.store import Store

        return Store(get_supabase_client(cfg))
    from jobintel.sqlite_store import SqliteStore

    return SqliteStore(cfg.local_db_path)
