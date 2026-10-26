"""backend/app/schemas/application.py — Pydantic schemas for the application engine."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.exc import NoInspectionAvailable

from app.models.application import ApplicationStatus, AttemptStatus, AnswerSource


# ── Answer ─────────────────────────────────────────────────────────────────────

class ApplicationAnswerRead(BaseModel):
    id: uuid.UUID
    question_text: str
    question_type: Optional[str] = None
    options: Optional[List[str]] = None
    answer: Optional[str] = None
    source: AnswerSource
    confidence: Optional[float] = None
    requires_user_input: bool

    model_config = {"from_attributes": True}


# ── Attempt ────────────────────────────────────────────────────────────────────

class ApplicationAttemptRead(BaseModel):
    id: uuid.UUID
    attempt_number: int
    status: AttemptStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    fields_detected: Optional[int] = None
    fields_filled: Optional[int] = None
    questions_detected: Optional[int] = None
    questions_answered: Optional[int] = None
    resume_uploaded: bool
    form_validated: bool
    would_submit: bool
    error_type: Optional[str] = None
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Application ────────────────────────────────────────────────────────────────

class ApplicationCreate(BaseModel):
    job_id: uuid.UUID
    resume_id: Optional[uuid.UUID] = None
    auto_apply_mode: Optional[str] = "safe"


class ApplicationUpdate(BaseModel):
    resume_id: Optional[uuid.UUID] = None
    status: Optional[ApplicationStatus] = None
    status_reason: Optional[str] = None
    warnings: Optional[List[str]] = None


class ApplicationRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    job_id: uuid.UUID
    resume_id: Optional[uuid.UUID] = None
    status: ApplicationStatus
    status_reason: Optional[str] = None
    is_eligible: Optional[bool] = None
    ineligibility_reasons: Optional[List[str]] = None
    match_score: Optional[int] = None
    match_explanation: Optional[str] = None
    match_threshold_used: Optional[int] = None
    application_method: Optional[str] = None
    can_submit_automatically: bool
    application_url: Optional[str] = None
    started_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    confirmation_id: Optional[str] = None
    attempt_count: int
    max_attempts: int
    last_error: Optional[str] = None
    warnings: Optional[List[str]] = None
    requires_user_input: bool
    user_input_question: Optional[str] = None
    auto_apply_mode: Optional[str] = None
    is_test_run: bool
    detected_fields: Optional[Dict[str, Any]] = None
    filled_fields: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    attempts: List[ApplicationAttemptRead] = []
    answers: List[ApplicationAnswerRead] = []

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def handle_unloaded_relationships(cls, data: Any) -> Any:
        try:
            insp = sa_inspect(data)
        except (NoInspectionAvailable, Exception):
            return data
        if insp is not None and hasattr(insp, "mapper"):
            res = {}
            for col in insp.mapper.column_attrs:
                if col.key not in insp.unloaded:
                    res[col.key] = getattr(data, col.key)
                else:
                    # Column attribute is unloaded or expired on flush
                    val = data.__dict__.get(col.key)
                    if val is not None:
                        res[col.key] = val
                    elif col.key in ("created_at", "updated_at"):
                        res[col.key] = datetime.now(timezone.utc)
            for rel in insp.mapper.relationships:
                if rel.key not in insp.unloaded:
                    res[rel.key] = getattr(data, rel.key)
                else:
                    res[rel.key] = [] if rel.uselist else None
            return res
        return data


class ApplicationQueueItem(BaseModel):
    """Lightweight item for the application queue list."""
    id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    status: ApplicationStatus
    company_name: str
    job_title: str
    match_score: Optional[int] = None
    application_method: Optional[str] = None
    application_url: Optional[str] = None
    job_url: Optional[str] = None
    resume_name: Optional[str] = None
    attempt_count: int
    requires_user_input: bool
    warnings: Optional[List[str]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApplicationReview(BaseModel):
    """
    Full review packet shown to the user before final submission (safe mode).
    """
    application_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    company_name: str
    job_title: str
    match_score: Optional[int] = None
    resume_name: Optional[str] = None
    application_method: Optional[str] = None
    application_url: Optional[str] = None
    job_url: Optional[str] = None
    status: Optional[str] = None
    cover_letter: Optional[str] = None
    job_description: Optional[str] = None
    answers: List[ApplicationAnswerRead] = []
    warnings: List[str] = []
    detected_fields: Optional[Dict[str, Any]] = None
    filled_fields: Optional[Dict[str, Any]] = None
    can_submit_automatically: bool = False
    is_test_run: bool = True


class ApplicationStats(BaseModel):
    """Aggregated stats for the dashboard."""
    stat_date: date
    jobs_found: int = 0
    jobs_eligible: int = 0
    jobs_matched: int = 0
    applications_submitted: int = 0
    applications_failed: int = 0
    applications_requiring_input: int = 0
    applications_started: int = 0
    daily_limit: int
    limit_reached: bool
    total: int = 0
    today: int = 0
    success_rate: int = 0
    auto_apply_enabled: bool = False
    queued: int = 0
    preparing: int = 0
    ready: int = 0
    submitted: int = 0
    failed: int = 0
    cancelled: int = 0
    daily_breakdown: Dict[str, int] = {}


class DryRunResult(BaseModel):
    """Result of POST /api/applications/test (dry run)."""
    job_id: uuid.UUID
    application_url: Optional[str] = None
    application_method: Optional[str] = None
    fields_detected: int = 0
    fields_filled: int = 0
    questions_detected: int = 0
    answers_generated: int = 0
    resume_uploaded: bool = False
    would_submit: bool = False
    warnings: List[str] = []
    errors: List[str] = []
    is_test_run: bool = True


class StatusTransitionRequest(BaseModel):
    new_status: ApplicationStatus
    reason: Optional[str] = None


# ── Auto-Apply Settings ────────────────────────────────────────────────────────

class AutoApplySettingsBase(BaseModel):
    is_enabled: bool = False
    mode: str = Field("safe", pattern="^(safe|auto)$")
    min_match_score: int = Field(90, ge=0, le=100)
    max_applications_per_day: int = Field(10, ge=1, le=100)
    delay_min_seconds: int = Field(30, ge=5)
    delay_max_seconds: int = Field(120, ge=5)
    max_retries: int = Field(3, ge=1, le=10)
    allowed_roles: Optional[List[str]] = None
    excluded_domains: Optional[List[str]] = None
    allowed_locations: Optional[List[str]] = None
    min_salary: Optional[int] = None
    salary_currency: Optional[str] = "INR"
    require_approval_before_submit: bool = True
    is_test_mode: bool = True


class AutoApplySettingsCreate(AutoApplySettingsBase):
    pass


class AutoApplySettingsUpdate(AutoApplySettingsBase):
    is_enabled: Optional[bool] = None  # type: ignore[assignment]
    mode: Optional[str] = None  # type: ignore[assignment]


class AutoApplySettingsRead(AutoApplySettingsBase):
    id: uuid.UUID
    user_id: uuid.UUID

    model_config = {"from_attributes": True}
