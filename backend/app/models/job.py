"""backend/app/models/job.py

Extends the Job model with fields needed for the job discovery pipeline.
Existing columns are preserved unchanged.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin, UUIDType
from app.utils.db_types import ArrayOfText, JsonBlob

if TYPE_CHECKING:
    from app.models.application import Application


class ApplicationMethod(str, enum.Enum):
    GREENHOUSE_API = "greenhouse_api"
    LEVER_API = "lever_api"
    BROWSER = "browser"
    MANUAL = "manual"
    UNKNOWN = "unknown"


class WorkMode(str, enum.Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    UNKNOWN = "unknown"


class JobSource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Registry of job discovery sources (Adzuna, Greenhouse, Lever, etc.)."""

    __tablename__ = "job_sources"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    base_url: Mapped[Optional[str]] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    jobs: Mapped[List["Job"]] = relationship("Job", back_populates="source")


class Job(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single job posting, discovered from any configured source.

    Deduplication strategy:
      Primary:  (source_job_id, source_id) — enforced by DB unique constraint.
      Fallback: fingerprint — SHA-256 hash of (source_name, company, title, canonical_url).

    New in discovery pipeline:
      canonical_url, fingerprint, work_mode, preferred_skills,
      posted_at, discovered_at, raw_data.
    """

    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("source_job_id", "source_id", name="uq_job_source"),
    )

    # ── Source tracking ───────────────────────────────────────────────────────
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUIDType(), ForeignKey("job_sources.id", ondelete="SET NULL"), index=True
    )
    source_job_id: Mapped[Optional[str]] = mapped_column(String(500), index=True)
    source_name: Mapped[Optional[str]] = mapped_column(String(100), index=True)

    # ── Core content ──────────────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    company_name: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    company_domain: Mapped[Optional[str]] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)
    requirements: Mapped[Optional[str]] = mapped_column(Text)

    # ── Location & work mode ──────────────────────────────────────────────────
    location: Mapped[Optional[str]] = mapped_column(String(300))
    is_remote: Mapped[Optional[bool]] = mapped_column(Boolean)
    is_hybrid: Mapped[Optional[bool]] = mapped_column(Boolean)
    work_mode: Mapped[Optional[str]] = mapped_column(
        String(20), default=WorkMode.UNKNOWN.value
    )

    # ── Requirements ──────────────────────────────────────────────────────────
    employment_type: Mapped[Optional[str]] = mapped_column(String(100))
    experience_min_years: Mapped[Optional[int]] = mapped_column(Integer)
    experience_max_years: Mapped[Optional[int]] = mapped_column(Integer)
    education_required: Mapped[Optional[str]] = mapped_column(String(200))
    graduation_year_required: Mapped[Optional[int]] = mapped_column(Integer)
    domain: Mapped[Optional[str]] = mapped_column(String(200))
    required_skills: Mapped[Optional[List[str]]] = mapped_column(ArrayOfText())
    preferred_skills: Mapped[Optional[List[str]]] = mapped_column(ArrayOfText())

    # ── Salary ────────────────────────────────────────────────────────────────
    salary_min: Mapped[Optional[int]] = mapped_column(Integer)
    salary_max: Mapped[Optional[int]] = mapped_column(Integer)
    salary_currency: Mapped[Optional[str]] = mapped_column(String(10))

    # ── URLs ──────────────────────────────────────────────────────────────────
    application_url: Mapped[Optional[str]] = mapped_column(String(1000))
    canonical_url: Mapped[Optional[str]] = mapped_column(String(1000), index=True)

    # ── Application method ────────────────────────────────────────────────────
    application_method: Mapped[ApplicationMethod] = mapped_column(
        Enum(ApplicationMethod, native_enum=False, create_constraint=False, length=50),
        default=ApplicationMethod.UNKNOWN,
        nullable=False,
    )
    can_submit_automatically: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── ATS-specific IDs ─────────────────────────────────────────────────────
    greenhouse_job_id: Mapped[Optional[str]] = mapped_column(String(200))
    greenhouse_board_token: Mapped[Optional[str]] = mapped_column(String(200))
    lever_posting_id: Mapped[Optional[str]] = mapped_column(String(200))

    # ── Matching & eligibility ────────────────────────────────────────────────
    match_score: Mapped[Optional[int]] = mapped_column(Integer)
    match_explanation: Mapped[Optional[str]] = mapped_column(Text)
    is_eligible: Mapped[Optional[bool]] = mapped_column(Boolean)
    eligibility_checked_at: Mapped[Optional[str]] = mapped_column(String(50))
    ineligibility_reasons: Mapped[Optional[List[str]]] = mapped_column(ArrayOfText())

    # ── Discovery metadata ────────────────────────────────────────────────────
    fingerprint: Mapped[Optional[str]] = mapped_column(String(64), index=True, unique=True)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    discovered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    raw_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JsonBlob())

    # ── Status flags ──────────────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    source: Mapped[Optional["JobSource"]] = relationship("JobSource", back_populates="jobs")
    applications: Mapped[List["Application"]] = relationship(
        "Application", back_populates="job"
    )
