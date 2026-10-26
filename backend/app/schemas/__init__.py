"""
backend/app/schemas/__init__.py
Re-exports all Pydantic schemas.
"""
from app.schemas.user import UserCreate, UserRead, UserUpdate, UserProfile
from app.schemas.resume import ResumeCreate, ResumeRead, ResumeUpdate
from app.schemas.job import JobCreate, JobRead, JobUpdate, JobListItem
from app.schemas.application import (
    ApplicationCreate,
    ApplicationRead,
    ApplicationUpdate,
    ApplicationQueueItem,
    ApplicationReview,
    ApplicationStats,
    DryRunResult,
    AutoApplySettingsCreate,
    AutoApplySettingsRead,
    AutoApplySettingsUpdate,
    ApplicationAnswerRead,
    ApplicationAttemptRead,
    StatusTransitionRequest,
)

__all__ = [
    "UserCreate", "UserRead", "UserUpdate", "UserProfile",
    "ResumeCreate", "ResumeRead", "ResumeUpdate",
    "JobCreate", "JobRead", "JobUpdate", "JobListItem",
    "ApplicationCreate", "ApplicationRead", "ApplicationUpdate",
    "ApplicationQueueItem", "ApplicationReview", "ApplicationStats",
    "DryRunResult", "AutoApplySettingsCreate", "AutoApplySettingsRead",
    "AutoApplySettingsUpdate", "ApplicationAnswerRead", "ApplicationAttemptRead",
    "StatusTransitionRequest",
]
