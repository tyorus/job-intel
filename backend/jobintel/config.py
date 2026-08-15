"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root: backend/jobintel/config.py -> parents[2]
_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime settings for batch jobs and local CLI."""

    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    supabase_anon_key: str | None = None

    openrouter_api_key: str | None = None
    openrouter_extraction_model: str = "openai/gpt-4o-mini"
    openrouter_resume_model: str = "openai/gpt-4o-mini"

    career_data_dir: Path = Field(default=_REPO_ROOT / "career_data")

    tracker_api_key: str | None = None
    tracker_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    scrape_keywords: str = (
        "python,data analyst,data engineer,data engineering,fastapi,etl,pandas,"
        "sql,pipeline,metocean,ocean,analytics,data cleaning,data visualization,automation"
    )
    scrape_max_per_source: int = 80
    collectors_config_path: Path = Field(
        default=Path(__file__).resolve().parent / "collectors" / "boards.yaml"
    )
    local_db_path: Path = Field(default=_REPO_ROOT / "data" / "tracker.sqlite")

    @field_validator("local_db_path", mode="after")
    @classmethod
    def _resolve_local_db(cls, value: Path) -> Path:
        return value if value.is_absolute() else (_REPO_ROOT / value)

    # Fit score weights (used from M4; documented defaults for M1)
    score_weight_skill: float = 0.35
    score_weight_experience: float = 0.25
    score_weight_role: float = 0.15
    score_weight_seniority: float = 0.10
    score_weight_location: float = 0.10
    score_weight_domain: float = 0.05

    @property
    def score_weights(self) -> dict[str, float]:
        return {
            "skill": self.score_weight_skill,
            "experience": self.score_weight_experience,
            "role": self.score_weight_role,
            "seniority": self.score_weight_seniority,
            "location": self.score_weight_location,
            "domain": self.score_weight_domain,
        }

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.tracker_cors_origins.split(",") if item.strip()]

    @property
    def keyword_list(self) -> list[str]:
        return [item.strip().lower() for item in self.scrape_keywords.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
