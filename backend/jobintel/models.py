"""Domain and career Pydantic models for Job Intelligence."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

# --- Enums -----------------------------------------------------------------


class RemoteType(StrEnum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    UNKNOWN = "unknown"


class JobStatus(StrEnum):
    NEW = "new"
    ANALYZED = "analyzed"
    SHORTLISTED = "shortlisted"
    CV_READY = "cv_ready"
    APPLIED = "applied"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    ARCHIVED = "archived"
    NOT_RELATED = "not_related"


class ApplicationStatus(StrEnum):
    NEW = "new"
    ANALYZED = "analyzed"
    SHORTLISTED = "shortlisted"
    CV_READY = "cv_ready"
    APPLIED = "applied"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    ARCHIVED = "archived"
    NOT_RELATED = "not_related"


class ProspectStatus(StrEnum):
    NEW = "new"
    CONTACTED = "contacted"
    REPLIED = "replied"
    CALL_BOOKED = "call_booked"
    PROPOSAL = "proposal"
    WON = "won"
    LOST = "lost"
    NURTURE = "nurture"
    CANCELLED = "cancelled"


class ServicePackage(StrEnum):
    AUDIT = "audit"
    BRIEF = "brief"
    RETAINER = "retainer"
    UNKNOWN = "unknown"


class ProgressEntityType(StrEnum):
    JOB = "job"
    PROSPECT = "prospect"


class ScoreBand(StrEnum):
    PRIORITY = "priority"
    APPLY = "apply"
    MAYBE = "maybe"
    SKIP = "skip"


SCORE_THRESHOLDS: dict[ScoreBand, tuple[int, int]] = {
    ScoreBand.PRIORITY: (85, 100),
    ScoreBand.APPLY: (70, 84),
    ScoreBand.MAYBE: (60, 69),
    ScoreBand.SKIP: (0, 59),
}


def score_band_for(total_score: float) -> ScoreBand:
    """Map a 0–100 fit score to a classification band."""
    score = max(0.0, min(100.0, float(total_score)))
    if score >= 85:
        return ScoreBand.PRIORITY
    if score >= 70:
        return ScoreBand.APPLY
    if score >= 60:
        return ScoreBand.MAYBE
    return ScoreBand.SKIP


# --- Job pipeline models ---------------------------------------------------


class Company(BaseModel):
    id: UUID | None = None
    name: str
    domain: str | None = None
    country: str | None = None
    created_at: datetime | None = None


class Job(BaseModel):
    id: UUID | None = None
    company_id: UUID | None = None
    title: str
    location: str | None = None
    country: str | None = None
    remote_type: RemoteType = RemoteType.UNKNOWN
    source: str = "manual"
    source_job_id: str | None = None
    url: str | None = None
    apply_url: str | None = None
    description: str
    posted_at: datetime | None = None
    deadline_at: datetime | None = None
    discovered_at: datetime | None = None
    salary_text: str | None = None
    employment_type: str | None = None
    department: str | None = None
    seniority: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    status: JobStatus = JobStatus.NEW
    content_hash: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class JobRequirements(BaseModel):
    """Structured extraction from a job description (M3)."""

    role_family: str | None = None
    seniority: str | None = None
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    minimum_years_experience: int | None = None
    education_requirement: str | None = None
    language_requirements: list[str] = Field(default_factory=list)
    location_requirements: list[str] = Field(default_factory=list)
    visa_notes: str | None = None
    salary_text: str | None = None


class JobAnalysis(BaseModel):
    id: UUID | None = None
    job_id: UUID
    role_family: str | None = None
    seniority: str | None = None
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    minimum_years_experience: int | None = None
    education_requirement: str | None = None
    language_requirements: list[str] = Field(default_factory=list)
    location_requirements: list[str] = Field(default_factory=list)
    visa_notes: str | None = None
    salary_text: str | None = None
    analysis_json: dict[str, Any] = Field(default_factory=dict)
    llm_provider: str | None = None
    llm_model: str | None = None
    created_at: datetime | None = None


class JobScore(BaseModel):
    id: UUID | None = None
    job_id: UUID
    total_score: float
    skill_score: float
    experience_score: float
    role_score: float
    seniority_score: float
    location_score: float
    domain_score: float
    explanation: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None

    @property
    def band(self) -> ScoreBand:
        return score_band_for(self.total_score)


class Application(BaseModel):
    id: UUID | None = None
    job_id: UUID
    status: ApplicationStatus = ApplicationStatus.NEW
    resume_version: int | None = None
    applied_at: datetime | None = None
    response_at: datetime | None = None
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ResumeVersion(BaseModel):
    id: UUID | None = None
    job_id: UUID
    version: int
    content_json: dict[str, Any] = Field(default_factory=dict)
    content_markdown: str = ""
    model: str | None = None
    created_at: datetime | None = None


class JobRead(Job):
    """Job row with denormalized company name for API responses."""

    company_name: str | None = None


class Prospect(BaseModel):
    id: UUID | None = None
    name: str
    company: str | None = None
    country: str | None = None
    role: str | None = None
    source: str | None = None
    potential_problem: str | None = None
    date_contacted: date | None = None
    channel: str | None = None
    proposal_sent: bool = False
    response: str | None = None
    status: ProspectStatus = ProspectStatus.NEW
    package: ServicePackage = ServicePackage.UNKNOWN
    follow_up_date: date | None = None
    next_action: str | None = None
    value_estimate_usd: float | None = None
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProgressEvent(BaseModel):
    id: UUID | None = None
    entity_type: ProgressEntityType
    entity_id: UUID
    status: str
    note: str | None = None
    created_at: datetime | None = None


class CollectedJob(BaseModel):
    """Normalized job from a public collector (before DB insert)."""

    title: str
    company_name: str
    url: str
    description: str
    location: str | None = None
    country: str | None = None
    remote_type: RemoteType = RemoteType.REMOTE
    source: str
    source_job_id: str | None = None
    posted_at: datetime | None = None
    deadline_at: datetime | None = None
    apply_url: str | None = None
    salary_text: str | None = None
    employment_type: str | None = None
    department: str | None = None
    seniority: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


# --- Career profile models -------------------------------------------------


class Skill(BaseModel):
    id: str
    name: str
    category: str
    aliases: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    scope: str | None = None  # e.g. project-scoped / freelance-scoped


class ExperienceBullet(BaseModel):
    id: str
    text: str
    tags: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)


class Experience(BaseModel):
    id: str
    company: str
    role: str
    start_date: str  # YYYY-MM
    end_date: str | None = None
    location: str | None = None
    employment_type: str | None = None
    remote_type: str | None = None
    include_in_default_resume: bool = True
    bullets: list[ExperienceBullet] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def _normalize_month(cls, value: object) -> object:
        if value is None or value == "":
            return None
        if isinstance(value, date):
            return value.strftime("%Y-%m")
        text = str(value).strip()
        if len(text) == 7 and text[4] == "-":
            return text
        if len(text) >= 10 and text[4] == "-" and text[7] == "-":
            return text[:7]
        raise ValueError(f"Expected YYYY-MM date, got {value!r}")


class ProjectBullet(BaseModel):
    id: str
    text: str
    tags: list[str] = Field(default_factory=list)


class Project(BaseModel):
    id: str
    name: str
    summary: str
    start_date: str | None = None
    end_date: str | None = None
    associated_with: str | None = None
    url: str | None = None
    include_in_default_resume: bool = True
    bullets: list[ProjectBullet] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)


class Education(BaseModel):
    id: str
    institution: str
    degree: str
    field: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    gpa: str | None = None
    details: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)


class Achievement(BaseModel):
    id: str
    kind: str  # award | certification | language | honor
    title: str
    issuer: str | None = None
    issued_on: str | None = None
    expires_on: str | None = None
    credential_id: str | None = None
    description: str | None = None
    proficiency: str | None = None
    tags: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)


class ProfileIdentity(BaseModel):
    full_name: str
    preferred_name: str | None = None
    headline: str
    location: str | None = None
    email: str | None = None
    website: HttpUrl | str | None = None
    linkedin: HttpUrl | str | None = None
    github: HttpUrl | str | None = None
    resume_pdf: HttpUrl | str | None = None
    open_to: list[str] = Field(default_factory=list)
    summary: str | None = None


class CareerProfile(BaseModel):
    profile: ProfileIdentity
    skills: list[Skill] = Field(default_factory=list)
    experiences: list[Experience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    achievements: list[Achievement] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_ids(self) -> CareerProfile:
        seen: set[str] = set()
        duplicates: list[str] = []

        def check(entity_id: str) -> None:
            if entity_id in seen:
                duplicates.append(entity_id)
            seen.add(entity_id)

        for skill in self.skills:
            check(skill.id)
        for exp in self.experiences:
            check(exp.id)
            for bullet in exp.bullets:
                check(bullet.id)
        for project in self.projects:
            check(project.id)
            for bullet in project.bullets:
                check(bullet.id)
        for edu in self.education:
            check(edu.id)
        for achievement in self.achievements:
            check(achievement.id)

        if duplicates:
            raise ValueError(f"Duplicate career IDs: {sorted(set(duplicates))}")
        return self
