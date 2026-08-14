"""Tests for career profile loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from jobintel.career.matching import normalize_skill_name
from jobintel.career.profile import CareerProfileError, load_career_profile
from jobintel.models import JobRequirements, ScoreBand, score_band_for

REPO_ROOT = Path(__file__).resolve().parents[2]
CAREER_DATA = REPO_ROOT / "career_data"


def test_load_seeded_career_profile() -> None:
    profile = load_career_profile(CAREER_DATA)
    assert profile.profile.full_name == "Suwignyo Prasetyo"
    assert any(e.id == "bmkg_metocean_de" for e in profile.experiences)
    assert any(e.id == "stmkg_basc_meteorology" for e in profile.education)
    assert any(s.category == "Data Analysis" for s in profile.skills)
    assert len(profile.skills) >= 10
    assert len(profile.experiences) >= 2
    assert len(profile.projects) >= 2


def test_malformed_yaml(tmp_path: Path) -> None:
    _copy_minimal_career(tmp_path)
    (tmp_path / "skills.yaml").write_text("skills: [\n  - id: broken\n", encoding="utf-8")
    with pytest.raises(CareerProfileError, match="Malformed YAML"):
        load_career_profile(tmp_path)


def test_missing_required_fields(tmp_path: Path) -> None:
    _copy_minimal_career(tmp_path)
    (tmp_path / "experiences.yaml").write_text(
        yaml.dump({"experiences": [{"id": "x", "company": "Acme"}]}),
        encoding="utf-8",
    )
    with pytest.raises(CareerProfileError, match="validation failed"):
        load_career_profile(tmp_path)


def test_duplicate_bullet_ids(tmp_path: Path) -> None:
    _copy_minimal_career(tmp_path)
    (tmp_path / "experiences.yaml").write_text(
        yaml.dump(
            {
                "experiences": [
                    {
                        "id": "job_a",
                        "company": "Acme",
                        "role": "Engineer",
                        "start_date": "2023-01",
                        "bullets": [
                            {"id": "dup", "text": "One"},
                            {"id": "dup", "text": "Two"},
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(CareerProfileError, match="Duplicate career IDs"):
        load_career_profile(tmp_path)


def test_missing_career_files(tmp_path: Path) -> None:
    with pytest.raises(CareerProfileError, match="Missing career data files"):
        load_career_profile(tmp_path)


def test_skill_alias_normalization() -> None:
    assert normalize_skill_name("k8s") == "Kubernetes"
    assert normalize_skill_name("ww3") == "WAVEWATCH III"
    assert normalize_skill_name("s3") == "S3"
    assert normalize_skill_name("Python") == "Python"


def test_score_band_thresholds() -> None:
    assert score_band_for(90) == ScoreBand.PRIORITY
    assert score_band_for(75) == ScoreBand.APPLY
    assert score_band_for(65) == ScoreBand.MAYBE
    assert score_band_for(40) == ScoreBand.SKIP


def test_job_requirements_round_trip() -> None:
    payload = {
        "role_family": "data_engineering",
        "seniority": "mid",
        "required_skills": ["Python", "SQL"],
        "preferred_skills": ["Prefect"],
        "responsibilities": ["build data pipelines"],
        "minimum_years_experience": 3,
        "education_requirement": None,
        "language_requirements": [],
        "location_requirements": ["Europe"],
        "visa_notes": None,
    }
    req = JobRequirements.model_validate(payload)
    assert req.model_dump() == {
        **payload,
        "salary_text": None,
    }


def _copy_minimal_career(target: Path) -> None:
    """Write a minimal valid career_data set for mutation tests."""
    (target / "profile.yaml").write_text(
        yaml.dump(
            {
                "full_name": "Test User",
                "headline": "Engineer",
            }
        ),
        encoding="utf-8",
    )
    (target / "skills.yaml").write_text(
        yaml.dump(
            {
                "skills": [
                    {
                        "id": "skill_python",
                        "name": "Python",
                        "category": "Data Engineering",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (target / "experiences.yaml").write_text(
        yaml.dump(
            {
                "experiences": [
                    {
                        "id": "job_a",
                        "company": "Acme",
                        "role": "Engineer",
                        "start_date": "2023-01",
                        "bullets": [{"id": "b1", "text": "Did things"}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (target / "projects.yaml").write_text(yaml.dump({"projects": []}), encoding="utf-8")
    (target / "education.yaml").write_text(
        yaml.dump(
            {
                "education": [
                    {
                        "id": "edu_1",
                        "institution": "Uni",
                        "degree": "BSc",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (target / "achievements.yaml").write_text(
        yaml.dump({"achievements": []}), encoding="utf-8"
    )
