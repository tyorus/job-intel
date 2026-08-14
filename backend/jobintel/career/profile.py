"""Career profile loading and validation from YAML files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from jobintel.config import get_settings
from jobintel.models import (
    Achievement,
    CareerProfile,
    Education,
    Experience,
    ProfileIdentity,
    Project,
    Skill,
)

REQUIRED_FILES = (
    "profile.yaml",
    "skills.yaml",
    "experiences.yaml",
    "projects.yaml",
    "education.yaml",
    "achievements.yaml",
)


class CareerProfileError(ValueError):
    """Raised when career YAML cannot be loaded or validated."""


def _load_yaml(path: Path) -> Any:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CareerProfileError(f"Cannot read {path}: {exc}") from exc
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise CareerProfileError(f"Malformed YAML in {path}: {exc}") from exc
    return data


def _as_list(data: Any, key: str, path: Path) -> list[Any]:
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and key in data:
        value = data[key]
        if value is None:
            return []
        if isinstance(value, list):
            return value
        raise CareerProfileError(f"{path}: expected list under '{key}'")
    raise CareerProfileError(f"{path}: expected a list or a mapping with key '{key}'")


def load_career_profile(career_dir: Path | None = None) -> CareerProfile:
    """Load and validate the full career profile from YAML files."""
    root = Path(career_dir) if career_dir is not None else get_settings().career_data_dir
    if not root.is_dir():
        raise CareerProfileError(f"Career data directory not found: {root}")

    missing = [name for name in REQUIRED_FILES if not (root / name).is_file()]
    if missing:
        raise CareerProfileError(f"Missing career data files in {root}: {missing}")

    profile_raw = _load_yaml(root / "profile.yaml")
    if not isinstance(profile_raw, dict):
        raise CareerProfileError("profile.yaml must be a mapping")

    # Allow either nested `profile:` or flat identity fields
    identity_data = profile_raw.get("profile", profile_raw)

    skills_raw = _as_list(_load_yaml(root / "skills.yaml"), "skills", root / "skills.yaml")
    experiences_raw = _as_list(
        _load_yaml(root / "experiences.yaml"), "experiences", root / "experiences.yaml"
    )
    projects_raw = _as_list(
        _load_yaml(root / "projects.yaml"), "projects", root / "projects.yaml"
    )
    education_raw = _as_list(
        _load_yaml(root / "education.yaml"), "education", root / "education.yaml"
    )
    achievements_raw = _as_list(
        _load_yaml(root / "achievements.yaml"),
        "achievements",
        root / "achievements.yaml",
    )

    try:
        return CareerProfile(
            profile=ProfileIdentity.model_validate(identity_data),
            skills=[Skill.model_validate(item) for item in skills_raw],
            experiences=[Experience.model_validate(item) for item in experiences_raw],
            projects=[Project.model_validate(item) for item in projects_raw],
            education=[Education.model_validate(item) for item in education_raw],
            achievements=[Achievement.model_validate(item) for item in achievements_raw],
        )
    except ValidationError as exc:
        raise CareerProfileError(f"Career profile validation failed:\n{exc}") from exc


def validate_career_profile(career_dir: Path | None = None) -> CareerProfile:
    """Alias used by CLI/tests; raises CareerProfileError on failure."""
    return load_career_profile(career_dir)
