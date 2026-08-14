"""Career matching helpers (stub for Milestone 4 fit scoring)."""

from __future__ import annotations

# Canonical aliases for skill normalization (expanded in M4).
SKILL_ALIASES: dict[str, str] = {
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "aws s3": "S3",
    "s3": "S3",
    "ww3": "WAVEWATCH III",
    "wavewatch iii": "WAVEWATCH III",
    "wavewatch3": "WAVEWATCH III",
}


def normalize_skill_name(name: str) -> str:
    """Normalize a skill/technology label using the alias map."""
    key = name.strip().lower()
    return SKILL_ALIASES.get(key, name.strip())
