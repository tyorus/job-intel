"""API request/response schemas for the tracker."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from jobintel.models import ProspectStatus, RemoteType, ServicePackage


class JobCreate(BaseModel):
    title: str
    description: str
    company_name: str | None = None
    url: str | None = None
    apply_url: str | None = None
    location: str | None = None
    country: str | None = None
    remote_type: RemoteType = RemoteType.UNKNOWN
    source: str = "manual"
    posted_at: datetime | None = None
    deadline_at: datetime | None = None
    salary_text: str | None = None
    employment_type: str | None = None
    department: str | None = None
    seniority: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None


class JobUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    url: str | None = None
    apply_url: str | None = None
    location: str | None = None
    country: str | None = None
    remote_type: RemoteType | None = None
    posted_at: datetime | None = None
    deadline_at: datetime | None = None
    salary_text: str | None = None
    employment_type: str | None = None
    department: str | None = None
    seniority: str | None = None
    tags: list[str] | None = None
    metadata_json: dict[str, Any] | None = None


class ProspectCreate(BaseModel):
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


class ProspectUpdate(BaseModel):
    name: str | None = None
    company: str | None = None
    country: str | None = None
    role: str | None = None
    source: str | None = None
    potential_problem: str | None = None
    date_contacted: date | None = None
    channel: str | None = None
    proposal_sent: bool | None = None
    response: str | None = None
    package: ServicePackage | None = None
    follow_up_date: date | None = None
    next_action: str | None = None
    value_estimate_usd: float | None = None
    notes: str | None = None


class ProgressIn(BaseModel):
    status: str
    note: str | None = None
