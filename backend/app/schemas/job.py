"""
backend/app/schemas/job.py — extended with discovery request/response schemas.
Existing JobBase, JobCreate, JobUpdate, JobRead, JobListItem are preserved.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.job import ApplicationMethod


# ── Existing schemas (unchanged) ───────────────────────────────────────────────

class JobBase(BaseModel):
    title: str
    company_name: str
    company_domain: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    location: Optional[str] = None
    is_remote: Optional[bool] = None
    is_hybrid: Optional[bool] = None
    work_mode: Optional[str] = None
    employment_type: Optional[str] = None
    experience_min_years: Optional[int] = None
    experience_max_years: Optional[int] = None
    education_required: Optional[str] = None
    graduation_year_required: Optional[int] = None
    domain: Optional[str] = None
    required_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None
    application_url: Optional[str] = None
    canonical_url: Optional[str] = None
    application_method: ApplicationMethod = ApplicationMethod.UNKNOWN
    can_submit_automatically: bool = False
    greenhouse_job_id: Optional[str] = None
    greenhouse_board_token: Optional[str] = None
    lever_posting_id: Optional[str] = None
    source_job_id: Optional[str] = None
    source_name: Optional[str] = None

    @model_validator(mode="after")
    def sync_urls(self) -> JobBase:
        if not self.application_url and self.canonical_url:
            self.application_url = self.canonical_url
        if not self.canonical_url and self.application_url:
            self.canonical_url = self.application_url
        return self


class JobCreate(JobBase):
    source_id: Optional[uuid.UUID] = None


class JobUpdate(JobBase):
    title: Optional[str] = None  # type: ignore[assignment]
    company_name: Optional[str] = None  # type: ignore[assignment]
    match_score: Optional[int] = None
    match_explanation: Optional[str] = None
    is_eligible: Optional[bool] = None
    ineligibility_reasons: Optional[List[str]] = None


class JobRead(JobBase):
    id: uuid.UUID
    source_id: Optional[uuid.UUID] = None
    source_name: Optional[str] = None
    match_score: Optional[int] = None
    match_explanation: Optional[str] = None
    is_eligible: Optional[bool] = None
    ineligibility_reasons: Optional[List[str]] = None
    fingerprint: Optional[str] = None
    posted_at: Optional[datetime] = None
    discovered_at: Optional[datetime] = None
    is_active: bool

    model_config = {"from_attributes": True}


class JobListItem(BaseModel):
    id: uuid.UUID
    title: str
    company_name: str
    location: Optional[str] = None
    work_mode: Optional[str] = None
    employment_type: Optional[str] = None
    application_method: ApplicationMethod
    match_score: Optional[int] = None
    is_eligible: Optional[bool] = None
    source_name: Optional[str] = None
    posted_at: Optional[datetime] = None
    discovered_at: Optional[datetime] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None
    application_url: Optional[str] = None
    canonical_url: Optional[str] = None
    experience_min_years: Optional[int] = None
    experience_max_years: Optional[int] = None
    required_skills: Optional[List[str]] = None
    description: Optional[str] = None

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def sync_urls(self) -> JobListItem:
        if not self.application_url and self.canonical_url:
            self.application_url = self.canonical_url
        if not self.canonical_url and self.application_url:
            self.canonical_url = self.application_url
        return self


# ── Discovery request/response schemas ────────────────────────────────────────

class JobDiscoverRequest(BaseModel):
    """Body for POST /api/v1/jobs/discover"""
    keywords: List[str] = Field(
        default_factory=list,
        description="Job title keywords or role names",
        max_length=10,
    )
    location: Optional[str] = Field(
        None,
        max_length=200,
        description="City, region or country",
    )
    country: Optional[str] = Field(
        None,
        max_length=5,
        description="ISO country code: 'in', 'gb', 'us', 'au'",
    )
    remote: Optional[bool] = Field(None, description="Filter to remote jobs only")
    employment_type: Optional[str] = Field(None, description="full-time | part-time | contract")
    salary_min: Optional[int] = Field(None, ge=0, description="Minimum salary")
    salary_max: Optional[int] = Field(None, ge=0, description="Maximum salary")
    experience_min_years: Optional[int] = Field(None, ge=0, le=50, description="Minimum years of experience")
    experience_max_years: Optional[int] = Field(None, ge=0, le=50, description="Maximum years of experience")
    experience_years: Optional[int] = Field(None, ge=0, le=50, description="Target years of experience")
    posted_within_days: Optional[int] = Field(
        None, ge=1, le=90, description="Only jobs posted in the last N days"
    )
    page: int = Field(1, ge=1, le=100)
    page_size: int = Field(20, ge=1, le=50)

    @field_validator("keywords")
    @classmethod
    def keywords_not_empty_strings(cls, v: List[str]) -> List[str]:
        return [kw.strip() for kw in v if kw.strip()]

    @field_validator("country")
    @classmethod
    def country_lowercase(cls, v: Optional[str]) -> Optional[str]:
        return v.lower() if v else None


class DiscoveryStatsSchema(BaseModel):
    sources_attempted: int
    sources_succeeded: int
    sources_failed: int
    source_errors: Dict[str, str] = {}
    jobs_fetched: int
    jobs_normalized: int
    jobs_new: int
    jobs_updated: int
    jobs_duplicates: int


class JobDiscoverResponse(BaseModel):
    success: bool
    stats: DiscoveryStatsSchema
    message: Optional[str] = None


class JobListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int
    items: List[JobListItem]
    jobs: Optional[List[JobListItem]] = None

    def model_post_init(self, __context: Any) -> None:
        if self.jobs is None:
            self.jobs = self.items


class JobDailyStats(BaseModel):
    """Real job statistics from the database."""
    total_jobs: int
    jobs_found_today: int
    jobs_eligible: int
    jobs_scored: int


class SourceStatus(BaseModel):
    name: str
    configured: bool
    status: str  # "ready" | "missing_credentials"


class SourceStatusResponse(BaseModel):
    sources: List[SourceStatus]
