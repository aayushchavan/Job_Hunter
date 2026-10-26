"""
backend/app/models/application.py  —  Application state machine + supporting models.

STATE TRANSITIONS (enforced in Application.transition_to):

  DISCOVERED  → ELIGIBLE | REJECTED | DUPLICATE
  ELIGIBLE    → MATCHED  | REJECTED
  MATCHED     → QUEUED   | REJECTED
  QUEUED      → PREPARING
  PREPARING   → REVIEW | SUBMITTING | FAILED | USER_INPUT_REQUIRED | CAPTCHA_REQUIRED
  REVIEW      → SUBMITTING | WITHDRAWN
  SUBMITTING  → SUBMITTED | FAILED | CAPTCHA_REQUIRED | USER_INPUT_REQUIRED
  SUBMITTED   → INTERVIEW | OFFER | WITHDRAWN
  FAILED      → QUEUED (retry) | WITHDRAWN
  USER_INPUT_REQUIRED → QUEUED | WITHDRAWN
  CAPTCHA_REQUIRED    → QUEUED | WITHDRAWN
  DUPLICATE / WITHDRAWN / REJECTED → (terminal, no further transitions)
  INTERVIEW   → OFFER | WITHDRAWN
  OFFER       → WITHDRAWN
"""
from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
    JSON, Boolean, Date, DateTime, Enum, ForeignKey, Integer,
    Numeric, String, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin, UUIDType
from app.utils.db_types import ArrayOfText

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.resume import Resume
    from app.models.job import Job


# ── Enums ──────────────────────────────────────────────────────────────────────

class ApplicationStatus(str, enum.Enum):
    DISCOVERED           = "DISCOVERED"
    ELIGIBLE             = "ELIGIBLE"
    MATCHED              = "MATCHED"
    QUEUED               = "QUEUED"
    PREPARING            = "PREPARING"
    REVIEW               = "REVIEW"
    SUBMITTING           = "SUBMITTING"
    SUBMITTED            = "SUBMITTED"
    FAILED               = "FAILED"
    REJECTED             = "REJECTED"
    USER_INPUT_REQUIRED  = "USER_INPUT_REQUIRED"
    CAPTCHA_REQUIRED     = "CAPTCHA_REQUIRED"
    DUPLICATE            = "DUPLICATE"
    WITHDRAWN            = "WITHDRAWN"
    INTERVIEW            = "INTERVIEW"
    OFFER                = "OFFER"


VALID_TRANSITIONS: dict[ApplicationStatus, set[ApplicationStatus]] = {
    ApplicationStatus.DISCOVERED: {
        ApplicationStatus.ELIGIBLE, ApplicationStatus.REJECTED, ApplicationStatus.DUPLICATE, ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.ELIGIBLE: {
        ApplicationStatus.MATCHED, ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN
    },
    ApplicationStatus.MATCHED: {
        ApplicationStatus.QUEUED, ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN
    },
    ApplicationStatus.QUEUED: {ApplicationStatus.PREPARING, ApplicationStatus.WITHDRAWN},
    ApplicationStatus.PREPARING: {
        ApplicationStatus.REVIEW, ApplicationStatus.SUBMITTING,
        ApplicationStatus.FAILED, ApplicationStatus.USER_INPUT_REQUIRED,
        ApplicationStatus.CAPTCHA_REQUIRED, ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.REVIEW: {ApplicationStatus.SUBMITTING, ApplicationStatus.WITHDRAWN},
    ApplicationStatus.SUBMITTING: {
        ApplicationStatus.SUBMITTED, ApplicationStatus.FAILED,
        ApplicationStatus.CAPTCHA_REQUIRED, ApplicationStatus.USER_INPUT_REQUIRED, ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.SUBMITTED: {
        ApplicationStatus.INTERVIEW, ApplicationStatus.OFFER, ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.FAILED: {ApplicationStatus.QUEUED, ApplicationStatus.WITHDRAWN},
    ApplicationStatus.USER_INPUT_REQUIRED: {ApplicationStatus.QUEUED, ApplicationStatus.WITHDRAWN},
    ApplicationStatus.CAPTCHA_REQUIRED:    {ApplicationStatus.QUEUED, ApplicationStatus.WITHDRAWN},
    ApplicationStatus.DUPLICATE:  set(),
    ApplicationStatus.WITHDRAWN:  {ApplicationStatus.QUEUED},
    ApplicationStatus.REJECTED:   set(),
    ApplicationStatus.INTERVIEW:  {ApplicationStatus.OFFER, ApplicationStatus.WITHDRAWN},
    ApplicationStatus.OFFER:      {ApplicationStatus.WITHDRAWN},
}


class AttemptStatus(str, enum.Enum):
    STARTED    = "STARTED"
    COMPLETED  = "COMPLETED"
    FAILED     = "FAILED"
    CAPTCHA    = "CAPTCHA"
    USER_INPUT = "USER_INPUT"


class AnswerSource(str, enum.Enum):
    USER_PROFILE = "user_profile"
    RESUME       = "resume"
    CLAUDE       = "claude"
    USER_INPUT   = "user_input"
    DEFAULT      = "default"


# ── Application ────────────────────────────────────────────────────────────────

class Application(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    One Application per (user, job) pair — enforced by UniqueConstraint.
    The status field drives the state machine.
    """

    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_application_user_job"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resume_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUIDType(), ForeignKey("resumes.id", ondelete="SET NULL")
    )

    # ── State machine ─────────────────────────────────────────────────────────
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, native_enum=False, create_constraint=False, length=30),
        default=ApplicationStatus.DISCOVERED,
        nullable=False,
        index=True,
    )
    status_reason: Mapped[Optional[str]] = mapped_column(Text)

    # ── Eligibility ───────────────────────────────────────────────────────────
    is_eligible: Mapped[Optional[bool]] = mapped_column(Boolean)
    ineligibility_reasons: Mapped[Optional[List[str]]] = mapped_column(ArrayOfText())

    # ── Match score ───────────────────────────────────────────────────────────
    match_score: Mapped[Optional[int]] = mapped_column(Integer)
    match_explanation: Mapped[Optional[str]] = mapped_column(Text)
    match_threshold_used: Mapped[Optional[int]] = mapped_column(Integer)

    # ── Application method ────────────────────────────────────────────────────
    application_method: Mapped[Optional[str]] = mapped_column(String(100))
    can_submit_automatically: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    application_url: Mapped[Optional[str]] = mapped_column(String(1000))

    # ── Submission tracking ───────────────────────────────────────────────────
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    confirmation_id: Mapped[Optional[str]] = mapped_column(String(500))

    # ── Retry tracking ────────────────────────────────────────────────────────
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    last_error: Mapped[Optional[str]] = mapped_column(Text)

    # ── Review / warnings ─────────────────────────────────────────────────────
    warnings: Mapped[Optional[List[str]]] = mapped_column(ArrayOfText())
    requires_user_input: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user_input_question: Mapped[Optional[str]] = mapped_column(Text)

    # ── Mode ──────────────────────────────────────────────────────────────────
    auto_apply_mode: Mapped[Optional[str]] = mapped_column(String(20))  # "safe" | "auto"
    is_test_run: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Form data captured during preparation ─────────────────────────────────
    detected_fields: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    filled_fields: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="applications")
    job: Mapped["Job"] = relationship("Job", back_populates="applications")
    resume: Mapped[Optional["Resume"]] = relationship("Resume", back_populates="applications")
    attempts: Mapped[List["ApplicationAttempt"]] = relationship(
        "ApplicationAttempt", back_populates="application",
        cascade="all, delete-orphan", order_by="ApplicationAttempt.created_at",
        lazy="selectin",
    )
    answers: Mapped[List["ApplicationAnswer"]] = relationship(
        "ApplicationAnswer", back_populates="application", cascade="all, delete-orphan",
        lazy="selectin",
    )

    # ── State machine methods ─────────────────────────────────────────────────

    def can_transition_to(self, new_status: ApplicationStatus) -> bool:
        return new_status in VALID_TRANSITIONS.get(self.status, set())

    def transition_to(self, new_status: ApplicationStatus, reason: str | None = None) -> None:
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Invalid transition: {self.status} → {new_status}. "
                f"Valid: {VALID_TRANSITIONS.get(self.status, set())}"
            )
        self.status = new_status
        if reason is not None:
            self.status_reason = reason

    @property
    def is_terminal(self) -> bool:
        return self.status in {
            ApplicationStatus.SUBMITTED,
            ApplicationStatus.REJECTED,
            ApplicationStatus.DUPLICATE,
            ApplicationStatus.WITHDRAWN,
        }

    @property
    def can_retry(self) -> bool:
        return (
            self.status == ApplicationStatus.FAILED
            and self.attempt_count < self.max_attempts
        )

    @property
    def is_actionable(self) -> bool:
        return self.status in {
            ApplicationStatus.REVIEW,
            ApplicationStatus.USER_INPUT_REQUIRED,
            ApplicationStatus.CAPTCHA_REQUIRED,
        }


# ── ApplicationAttempt ────────────────────────────────────────────────────────

class ApplicationAttempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Tracks each individual attempt — max 3 by default."""

    __tablename__ = "application_attempts"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[AttemptStatus] = mapped_column(
        Enum(AttemptStatus, native_enum=False, create_constraint=False, length=20),
        default=AttemptStatus.STARTED, nullable=False,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    fields_detected:   Mapped[Optional[int]] = mapped_column(Integer)
    fields_filled:     Mapped[Optional[int]] = mapped_column(Integer)
    questions_detected: Mapped[Optional[int]] = mapped_column(Integer)
    questions_answered: Mapped[Optional[int]] = mapped_column(Integer)
    resume_uploaded:   Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    form_validated:    Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    would_submit:      Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    error_type:        Mapped[Optional[str]] = mapped_column(String(200))
    error_message:     Mapped[Optional[str]] = mapped_column(Text)
    error_stacktrace:  Mapped[Optional[str]] = mapped_column(Text)
    step_log:          Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON)

    application: Mapped["Application"] = relationship("Application", back_populates="attempts")


# ── ApplicationAnswer ─────────────────────────────────────────────────────────

class ApplicationAnswer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single question-answer pair generated during application preparation.
    Answers are NEVER fabricated — if Claude can't answer, requires_user_input=True.
    """

    __tablename__ = "application_answers"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[Optional[str]] = mapped_column(String(50))
    options: Mapped[Optional[List[str]]] = mapped_column(ArrayOfText())

    answer: Mapped[Optional[str]] = mapped_column(Text)
    source: Mapped[AnswerSource] = mapped_column(
        Enum(AnswerSource, native_enum=False, create_constraint=False, length=20),
        default=AnswerSource.CLAUDE, nullable=False,
    )
    confidence: Mapped[Optional[float]] = mapped_column(Numeric(4, 3))
    requires_user_input: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    application: Mapped["Application"] = relationship("Application", back_populates="answers")


# ── AutoApplySettings ─────────────────────────────────────────────────────────

class AutoApplySettings(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Per-user auto-apply configuration stored in DB."""

    __tablename__ = "auto_apply_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mode: Mapped[str] = mapped_column(String(20), default="safe", nullable=False)

    min_match_score: Mapped[int] = mapped_column(Integer, default=90, nullable=False)
    max_applications_per_day: Mapped[int] = mapped_column(Integer, default=10, nullable=False)

    delay_min_seconds: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    delay_max_seconds: Mapped[int] = mapped_column(Integer, default=120, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    allowed_roles: Mapped[Optional[List[str]]] = mapped_column(ArrayOfText())
    excluded_domains: Mapped[Optional[List[str]]] = mapped_column(ArrayOfText())
    allowed_locations: Mapped[Optional[List[str]]] = mapped_column(ArrayOfText())
    min_salary: Mapped[Optional[int]] = mapped_column(Integer)
    salary_currency: Mapped[Optional[str]] = mapped_column(String(10), default="INR")

    require_approval_before_submit: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_test_mode: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="auto_apply_settings")


# ── ApplicationDailyStats ─────────────────────────────────────────────────────

class ApplicationDailyStats(Base):
    """One row per (user, date). Used for daily limit enforcement."""

    __tablename__ = "application_daily_stats"
    __table_args__ = (
        UniqueConstraint("user_id", "stat_date", name="uq_daily_stats_user_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stat_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    applications_started:          Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    applications_submitted:        Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    applications_failed:           Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    applications_rejected:         Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    applications_requiring_input:  Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
