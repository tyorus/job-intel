"""Career package exports."""

from jobintel.career.matching import SKILL_ALIASES, normalize_skill_name
from jobintel.career.profile import (
    CareerProfileError,
    load_career_profile,
    validate_career_profile,
)

__all__ = [
    "CareerProfileError",
    "SKILL_ALIASES",
    "load_career_profile",
    "normalize_skill_name",
    "validate_career_profile",
]
