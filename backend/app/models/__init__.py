"""
backend/app/models/__init__.py
Re-exports all ORM models so Alembic auto-detects them.
"""
from app.models.user import User
from app.models.resume import Resume
from app.models.job import Job, JobSource
from app.models.eligibility import EligibilityCriteria
from app.models.application import (
    Application,
    ApplicationAttempt,
    ApplicationAnswer,
    AutoApplySettings,
    ApplicationDailyStats,
)

__all__ = [
    "User",
    "Resume",
    "Job",
    "JobSource",
    "EligibilityCriteria",
    "Application",
    "ApplicationAttempt",
    "ApplicationAnswer",
    "AutoApplySettings",
    "ApplicationDailyStats",
]
