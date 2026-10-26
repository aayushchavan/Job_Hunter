"""
backend/app/services/application_service.py

Application Service
====================
Responsible for:
  - Creating applications (with duplicate protection)
  - State machine transitions (with validation)
  - Daily limit enforcement
  - Application queue management
  - Stats aggregation
  - Browser automation orchestration (BrowserApplicationService)

All database operations are async.
Browser automation uses Playwright via app.browser package.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.application import (
    Application,
    ApplicationAnswer,
    ApplicationAttempt,
    ApplicationDailyStats,
    ApplicationStatus,
    AttemptStatus,
    AutoApplySettings,
    VALID_TRANSITIONS,
)
from app.models.job import Job
from app.models.resume import Resume
from app.models.user import User
from app.schemas.application import (
    ApplicationCreate,
    ApplicationQueueItem,
    ApplicationReview,
    ApplicationStats,
    AutoApplySettingsCreate,
    AutoApplySettingsUpdate,
    DryRunResult,
)


class DuplicateApplicationError(Exception):
    """Raised when attempting to create a duplicate application."""


class DailyLimitReachedError(Exception):
    """Raised when the daily application limit has been reached."""


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""


class ApplicationService:
    """
    Service layer for the application engine.
    All public methods accept an AsyncSession and operate within it.
    """

    # ── Creation ──────────────────────────────────────────────────────────────

    async def create_application(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        job_id: uuid.UUID,
        resume_id: Optional[uuid.UUID] = None,
        auto_apply_mode: str = "safe",
        is_test_run: bool = True,
    ) -> Application:
        """
        Create a new Application record with DISCOVERED status.

        Checks:
          1. Duplicate — if the same user+job already exists, raises DuplicateApplicationError.
          2. The Application is created in DISCOVERED state.

        Does NOT check the daily limit at creation time — that is checked
        when the application actually starts preparation (PREPARING state).
        """
        # ── Fetch job to copy relevant fields ─────────────────────────────────
        job = await db.get(Job, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        # ── Duplicate protection / reactivation ───────────────────────────────
        existing = await self._get_existing(db, user_id, job_id)
        if existing:
            if existing.status == ApplicationStatus.WITHDRAWN:
                # Re-activate and re-queue previously cancelled application
                existing.status = ApplicationStatus.QUEUED
                existing.status_reason = "Application re-queued by user"
                if resume_id:
                    existing.resume_id = resume_id
                existing.auto_apply_mode = auto_apply_mode
                existing.is_test_run = is_test_run
                await db.flush()
                return existing

            status_display = (
                existing.status.value.replace("_", " ").title()
                if hasattr(existing.status, "value")
                else str(existing.status).replace("_", " ").title()
            )
            raise DuplicateApplicationError(
                f"You already have an application for '{job.title}' at '{job.company_name}' (Current status: {status_display})."
            )

        # Handle both Enum and str for application_method
        method = job.application_method
        method_value = method.value if hasattr(method, "value") else str(method) if method else None

        app_url = job.application_url or job.canonical_url
        app = Application(
            user_id=user_id,
            job_id=job_id,
            resume_id=resume_id,
            status=ApplicationStatus.QUEUED,
            application_method=method_value,
            can_submit_automatically=job.can_submit_automatically,
            application_url=app_url,
            auto_apply_mode=auto_apply_mode,
            is_test_run=is_test_run,
            max_attempts=settings.AUTO_APPLY_MAX_RETRIES,
            attempts=[],
            answers=[],
        )
        db.add(app)
        await db.flush()  # get the ID without committing
        return app

    # ── State machine ─────────────────────────────────────────────────────────

    async def transition(
        self,
        db: AsyncSession,
        application_id: uuid.UUID,
        new_status: ApplicationStatus,
        reason: Optional[str] = None,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> Application:
        """
        Apply a validated state transition to an Application.
        Raises InvalidTransitionError if the transition is illegal.
        """
        app = await self.get_by_id(db, application_id)
        if app is None:
            raise ValueError(f"Application {application_id} not found")

        if not app.can_transition_to(new_status):
            raise InvalidTransitionError(
                f"Cannot transition from {app.status} to {new_status}. "
                f"Valid: {VALID_TRANSITIONS.get(app.status, set())}"
            )

        app.status = new_status
        if reason:
            app.status_reason = reason

        # Apply extra fields (e.g., match_score, submitted_at)
        if extra_fields:
            for k, v in extra_fields.items():
                if hasattr(app, k):
                    setattr(app, k, v)

        # Side effects on specific transitions
        if new_status == ApplicationStatus.PREPARING:
            app.started_at = datetime.now(timezone.utc)
            app.attempt_count += 1
            await self._increment_daily_stat(db, app.user_id, "applications_started")

        elif new_status == ApplicationStatus.SUBMITTED:
            app.submitted_at = datetime.now(timezone.utc)
            await self._increment_daily_stat(db, app.user_id, "applications_submitted")

        elif new_status == ApplicationStatus.FAILED:
            await self._increment_daily_stat(db, app.user_id, "applications_failed")

        elif new_status == ApplicationStatus.REJECTED:
            await self._increment_daily_stat(db, app.user_id, "applications_rejected")

        elif new_status == ApplicationStatus.USER_INPUT_REQUIRED:
            app.requires_user_input = True
            await self._increment_daily_stat(db, app.user_id, "applications_requiring_input")

        await db.flush()
        return app

    # ── Daily limit ───────────────────────────────────────────────────────────

    async def check_daily_limit(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: Optional[int] = None,
    ) -> Tuple[int, int, bool]:
        """
        Returns (applications_today, limit, limit_reached).
        Reads from application_daily_stats or counts directly.
        """
        effective_limit = limit or settings.AUTO_APPLY_MAX_PER_DAY
        today = date.today()

        row = await db.scalar(
            select(ApplicationDailyStats).where(
                and_(
                    ApplicationDailyStats.user_id == user_id,
                    ApplicationDailyStats.stat_date == today,
                )
            )
        )
        if row is None:
            return 0, effective_limit, False

        count = row.applications_started
        return count, effective_limit, count >= effective_limit

    async def enforce_daily_limit(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: Optional[int] = None,
    ) -> None:
        """
        Raises DailyLimitReachedError if the limit is already reached.
        """
        count, lim, reached = await self.check_daily_limit(db, user_id, limit)
        if reached:
            raise DailyLimitReachedError(
                f"Daily application limit reached: {count}/{lim}. "
                "No more applications will be processed today."
            )

    # ── Queue ─────────────────────────────────────────────────────────────────

    async def get_queue(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        statuses: Optional[List[ApplicationStatus]] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ApplicationQueueItem]:
        """
        Return the application queue for a user.
        Defaults to active/actionable statuses.
        """
        if status_filter and status_filter.lower() != "all":
            sf = status_filter.lower()
            if sf == "queued":
                statuses = [ApplicationStatus.QUEUED, ApplicationStatus.DISCOVERED, ApplicationStatus.MATCHED]
            elif sf == "preparing":
                statuses = [ApplicationStatus.PREPARING]
            elif sf in {"ready", "review"}:
                statuses = [ApplicationStatus.REVIEW]
            elif sf == "submitted":
                statuses = [ApplicationStatus.SUBMITTED]
            elif sf == "failed":
                statuses = [ApplicationStatus.FAILED]
            elif sf in {"cancelled", "withdrawn"}:
                statuses = [ApplicationStatus.WITHDRAWN]
            else:
                try:
                    statuses = [ApplicationStatus(sf.upper())]
                except ValueError:
                    statuses = None

        if statuses is None:
            statuses = [
                ApplicationStatus.QUEUED,
                ApplicationStatus.DISCOVERED,
                ApplicationStatus.MATCHED,
                ApplicationStatus.PREPARING,
                ApplicationStatus.REVIEW,
                ApplicationStatus.SUBMITTING,
                ApplicationStatus.SUBMITTED,
                ApplicationStatus.USER_INPUT_REQUIRED,
                ApplicationStatus.CAPTCHA_REQUIRED,
                ApplicationStatus.FAILED,
            ]

        result = await db.execute(
            select(Application)
            .options(
                selectinload(Application.job),
                selectinload(Application.resume),
            )
            .where(
                and_(
                    Application.user_id == user_id,
                    Application.status.in_(statuses),
                )
            )
            .order_by(Application.match_score.desc().nulls_last(), Application.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        apps = result.scalars().all()

        return [
            ApplicationQueueItem(
                id=a.id,
                job_id=a.job_id,
                status=a.status,
                company_name=a.job.company_name if a.job else "Unknown",
                job_title=a.job.title if a.job else "Unknown",
                match_score=a.match_score,
                application_method=a.application_method,
                application_url=a.application_url or (a.job.application_url if a.job else None) or (a.job.canonical_url if a.job else None),
                job_url=a.application_url or (a.job.application_url if a.job else None) or (a.job.canonical_url if a.job else None),
                resume_name=a.resume.name if a.resume else None,
                attempt_count=a.attempt_count,
                requires_user_input=a.requires_user_input,
                warnings=a.warnings,
                created_at=a.created_at,
            )
            for a in apps
        ]

    # ── Stats ─────────────────────────────────────────────────────────────────

    async def get_stats(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        target_date: Optional[date] = None,
    ) -> ApplicationStats:
        """Return today's aggregated application statistics."""
        from datetime import datetime, timezone, timedelta
        if target_date is None:
            target_date = date.today()

        row = await db.scalar(
            select(ApplicationDailyStats).where(
                and_(
                    ApplicationDailyStats.user_id == user_id,
                    ApplicationDailyStats.stat_date == target_date,
                )
            )
        )

        # Get settings for the daily limit
        user_settings = await self._get_or_create_settings(db, user_id)
        daily_limit = user_settings.max_applications_per_day

        # Count total eligible + matched jobs from the job table
        eligible_count = await db.scalar(
            select(func.count(Job.id)).where(Job.is_eligible == True)
        ) or 0

        # Count jobs discovered today
        today_start = datetime(
            target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc
        )
        jobs_found_today = await db.scalar(
            select(func.count(Job.id)).where(Job.discovered_at >= today_start)
        ) or 0

        # Count jobs that have a match score (scored by matching engine)
        jobs_scored_today = await db.scalar(
            select(func.count(Job.id)).where(
                Job.discovered_at >= today_start,
                Job.match_score.is_not(None),
            )
        ) or 0

        # Application pipeline breakdown from DB
        app_rows = await db.execute(
            select(Application.status, func.count(Application.id))
            .where(Application.user_id == user_id)
            .group_by(Application.status)
        )
        status_counts = dict(app_rows.all())
        queued_count = (
            status_counts.get(ApplicationStatus.QUEUED, 0)
            + status_counts.get(ApplicationStatus.DISCOVERED, 0)
            + status_counts.get(ApplicationStatus.MATCHED, 0)
        )
        preparing_count = status_counts.get(ApplicationStatus.PREPARING, 0)
        ready_count = status_counts.get(ApplicationStatus.REVIEW, 0)
        submitted_count = status_counts.get(ApplicationStatus.SUBMITTED, 0)
        failed_count = status_counts.get(ApplicationStatus.FAILED, 0)
        cancelled_count = status_counts.get(ApplicationStatus.WITHDRAWN, 0)
        total_apps = sum(status_counts.values())

        # Success rate
        submitted = (row.applications_submitted if row else 0) or submitted_count
        started = (row.applications_started if row else 0) or total_apps
        success_rate = round((submitted / started * 100)) if started > 0 else 0

        # Build past 7 days daily breakdown
        daily_breakdown = {}
        for d in range(6, -1, -1):
            day_date = target_date - timedelta(days=d)
            daily_breakdown[day_date.isoformat()] = 0

        past_stats = await db.execute(
            select(ApplicationDailyStats.stat_date, ApplicationDailyStats.applications_submitted)
            .where(
                and_(
                    ApplicationDailyStats.user_id == user_id,
                    ApplicationDailyStats.stat_date >= (target_date - timedelta(days=6)),
                )
            )
        )
        for stat_d, count in past_stats.all():
            if stat_d.isoformat() in daily_breakdown:
                daily_breakdown[stat_d.isoformat()] = count

        return ApplicationStats(
            stat_date=target_date,
            jobs_found=jobs_found_today,
            jobs_eligible=eligible_count,
            jobs_matched=jobs_scored_today,
            applications_submitted=submitted,
            applications_failed=row.applications_failed if row else failed_count,
            applications_requiring_input=row.applications_requiring_input if row else 0,
            applications_started=started,
            daily_limit=daily_limit,
            limit_reached=started >= daily_limit,
            total=total_apps,
            today=submitted,
            success_rate=success_rate,
            auto_apply_enabled=user_settings.is_enabled,
            queued=queued_count,
            preparing=preparing_count,
            ready=ready_count,
            submitted=submitted_count,
            failed=failed_count,
            cancelled=cancelled_count,
            daily_breakdown=daily_breakdown,
        )

    # ── Review packet ──────────────────────────────────────────────────────────

    async def get_review(
        self,
        db: AsyncSession,
        application_id: uuid.UUID,
    ) -> ApplicationReview:
        """Build the review packet shown to the user before submission."""
        query = (
            select(Application)
            .options(
                selectinload(Application.job),
                selectinload(Application.resume),
                selectinload(Application.user),
                selectinload(Application.answers),
            )
            .where(Application.id == application_id)
        )
        res = await db.execute(query)
        app = res.scalar_one_or_none()
        if not app:
            raise ValueError(f"Application {application_id} not found")

        app_url = (
            app.application_url
            or (app.job.application_url if app.job else None)
            or (app.job.canonical_url if app.job else None)
        )

        if not app.application_url and app_url:
            app.application_url = app_url
            await db.commit()

        company = (app.job.company_name if app.job else None) or "Company"
        title = (app.job.title if app.job else None) or "Software Engineer"
        status_str = app.status.value if hasattr(app.status, "value") else str(app.status)

        candidate_name = (
            f"{app.user.first_name} {app.user.last_name}".strip()
            if app.user and (app.user.first_name or app.user.last_name)
            else "Candidate"
        )
        skills_str = (
            ", ".join((app.resume.extracted_skills or ["modern software engineering"])[:4])
            if app.resume
            else "Full Stack Engineering"
        )

        cover_letter = (
            f"Dear Hiring Team at {company},\n\n"
            f"I am writing to express my strong interest in the {title} role. "
            f"With proven hands-on experience across {skills_str}, I specialize in building "
            f"scalable, reliable, and high-performance solutions.\n\n"
            f"I am eager to contribute to {company}'s engineering objectives and would welcome "
            f"the opportunity to discuss how my technical qualifications align with your requirements.\n\n"
            f"Sincerely,\n{candidate_name}"
        )

        return ApplicationReview(
            application_id=app.id,
            job_id=app.job_id,
            company_name=company,
            job_title=title,
            match_score=app.match_score,
            resume_name=app.resume.name if app.resume else None,
            application_method=app.application_method,
            application_url=app_url,
            job_url=app_url,
            status=status_str,
            cover_letter=cover_letter,
            job_description=app.job.description if app.job else None,
            answers=[
                {
                    "id": a.id,
                    "question_text": a.question_text,
                    "question_type": a.question_type,
                    "options": a.options,
                    "answer": a.answer,
                    "source": a.source,
                    "confidence": float(a.confidence) if a.confidence else None,
                    "requires_user_input": a.requires_user_input,
                }
                for a in app.answers
            ],
            warnings=app.warnings or [],
            detected_fields=app.detected_fields,
            filled_fields=app.filled_fields,
            can_submit_automatically=app.can_submit_automatically,
            is_test_run=app.is_test_run,
        )

    # ── Dry run ────────────────────────────────────────────────────────────────

    async def dry_run(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        job_id: uuid.UUID,
        resume_id: Optional[uuid.UUID] = None,
    ) -> DryRunResult:
        """
        Simulate an application without submitting.
        Phase 1: Returns a stub result. Phase 3+ fills it with real data.
        """
        job = await db.get(Job, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        # Phase 1 stub — later phases will call the browser engine here
        return DryRunResult(
            job_id=job_id,
            application_url=job.application_url,
            application_method=job.application_method.value if job.application_method else None,
            fields_detected=0,
            fields_filled=0,
            questions_detected=0,
            answers_generated=0,
            resume_uploaded=False,
            would_submit=False,
            warnings=["Dry run is a stub in Phase 1. Browser engine not yet active."],
            errors=[],
            is_test_run=True,
        )

    # ── Settings ──────────────────────────────────────────────────────────────

    async def get_or_create_settings(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> AutoApplySettings:
        return await self._get_or_create_settings(db, user_id)

    async def update_settings(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        payload: AutoApplySettingsUpdate,
    ) -> AutoApplySettings:
        s = await self._get_or_create_settings(db, user_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(s, field, value)
        await db.flush()
        return s

    # ── Retry ─────────────────────────────────────────────────────────────────

    async def retry(
        self,
        db: AsyncSession,
        application_id: uuid.UUID,
    ) -> Application:
        """
        Re-queue a FAILED application if retries remain.
        """
        app = await self.get_by_id(db, application_id)
        if app is None:
            raise ValueError(f"Application {application_id} not found")

        if app.status != ApplicationStatus.FAILED:
            raise InvalidTransitionError(
                f"Only FAILED applications can be retried. Current status: {app.status}"
            )
        if not app.can_retry:
            raise InvalidTransitionError(
                f"Maximum retries ({app.max_attempts}) reached for application {application_id}"
            )

        return await self.transition(db, application_id, ApplicationStatus.QUEUED, "Manual retry")

    # ── Cancellation ──────────────────────────────────────────────────────────

    async def cancel(
        self,
        db: AsyncSession,
        application_id: uuid.UUID,
        reason: str = "Cancelled by user",
    ) -> Application:
        """Withdraw an application (if not already terminal)."""
        app = await self.get_by_id(db, application_id)
        if app is None:
            raise ValueError(f"Application {application_id} not found")

        if app.status == ApplicationStatus.WITHDRAWN:
            return app

        if app.is_terminal and app.status not in {ApplicationStatus.SUBMITTED}:
            raise InvalidTransitionError(
                f"Application is already in terminal state: {app.status}"
            )

        return await self.transition(db, application_id, ApplicationStatus.WITHDRAWN, reason)

    # ── Lookups ───────────────────────────────────────────────────────────────

    async def get_by_id(
        self,
        db: AsyncSession,
        application_id: uuid.UUID,
    ) -> Optional[Application]:
        return await db.get(Application, application_id)

    async def get_by_id_full(
        self,
        db: AsyncSession,
        application_id: uuid.UUID,
    ) -> Optional[Application]:
        """Load application with all relationships."""
        result = await db.execute(
            select(Application)
            .options(
                selectinload(Application.job),
                selectinload(Application.resume),
                selectinload(Application.answers),
                selectinload(Application.attempts),
            )
            .where(Application.id == application_id)
        )
        return result.scalar_one_or_none()

    async def list_applications(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        status: Optional[ApplicationStatus] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Application]:
        q = select(Application).options(
            selectinload(Application.job),
            selectinload(Application.resume),
        ).where(Application.user_id == user_id)

        if status:
            q = q.where(Application.status == status)

        q = q.order_by(Application.created_at.desc()).limit(limit).offset(offset)
        result = await db.execute(q)
        return list(result.scalars().all())

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _get_existing(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        job_id: uuid.UUID,
    ) -> Optional[Application]:
        result = await db.execute(
            select(Application).where(
                and_(
                    Application.user_id == user_id,
                    Application.job_id == job_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def _get_or_create_settings(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> AutoApplySettings:
        result = await db.execute(
            select(AutoApplySettings).where(AutoApplySettings.user_id == user_id)
        )
        s = result.scalar_one_or_none()
        if s is None:
            s = AutoApplySettings(
                user_id=user_id,
                is_enabled=settings.AUTO_APPLY_ENABLED,
                mode=settings.AUTO_APPLY_MODE,
                min_match_score=settings.AUTO_APPLY_THRESHOLD,
                max_applications_per_day=settings.AUTO_APPLY_MAX_PER_DAY,
                delay_min_seconds=settings.AUTO_APPLY_DELAY_MIN_SEC,
                delay_max_seconds=settings.AUTO_APPLY_DELAY_MAX_SEC,
                max_retries=settings.AUTO_APPLY_MAX_RETRIES,
                is_test_mode=settings.AUTO_APPLY_TEST_MODE,
            )
            db.add(s)
            await db.flush()
        return s

    async def _increment_daily_stat(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        field: str,
    ) -> None:
        """Upsert the daily stats row and increment the specified counter."""
        today = date.today()
        row = await db.scalar(
            select(ApplicationDailyStats).where(
                and_(
                    ApplicationDailyStats.user_id == user_id,
                    ApplicationDailyStats.stat_date == today,
                )
            )
        )
        if row is None:
            row = ApplicationDailyStats(
                user_id=user_id,
                stat_date=today,
            )
            db.add(row)
            await db.flush()

        current = getattr(row, field, 0) or 0
        setattr(row, field, current + 1)
        await db.flush()


# ── Singleton ──────────────────────────────────────────────────────────────────
application_service = ApplicationService()


# ══════════════════════════════════════════════════════════════════════════════
# BrowserApplicationService
# ══════════════════════════════════════════════════════════════════════════════

class BrowserApplicationService:
    """
    Orchestrates the complete automated job application flow:

      1. Load user profile + resume from DB
      2. Call BrowserEngine to navigate → detect → fill → (optionally) submit
      3. Save detected fields, filled fields, AI answers to DB
      4. Advance Application state machine
      5. Record AttemptLog

    Integrated here so the project stays in a single services file.
    """

    def __init__(self) -> None:
        self._app_svc = application_service

    async def prepare_and_fill(
        self,
        db: AsyncSession,
        application_id: uuid.UUID,
        force_submit: bool = False,
    ) -> Application:
        """
        Main entry point. Runs browser automation for the given application.

        Steps:
          1. Load application + user + resume
          2. Check daily limit
          3. Transition to PREPARING
          4. Run BrowserEngine
          5. Save results to DB
          6. Transition to REVIEW (safe) or SUBMITTING (auto)
        """
        from app.browser.browser_engine import BrowserEngine, BrowserEngineResult
        from app.ai.factory import get_ai_provider

        # ── 1. Load application ────────────────────────────────────────────────
        app = await self._app_svc.get_by_id_full(db, application_id)
        if not app:
            raise ValueError(f"Application {application_id} not found")

        if app.status in {
            ApplicationStatus.WITHDRAWN,
            ApplicationStatus.FAILED,
            ApplicationStatus.USER_INPUT_REQUIRED,
            ApplicationStatus.CAPTCHA_REQUIRED,
        }:
            app = await self._app_svc.transition(db, application_id, ApplicationStatus.QUEUED, reason="Re-queued for preparation")
        elif app.status in {ApplicationStatus.DISCOVERED, ApplicationStatus.ELIGIBLE}:
            if app.status == ApplicationStatus.DISCOVERED:
                app = await self._app_svc.transition(db, application_id, ApplicationStatus.ELIGIBLE, reason="Advance for preparation")
            app = await self._app_svc.transition(db, application_id, ApplicationStatus.MATCHED, reason="Advance for preparation")
            app = await self._app_svc.transition(db, application_id, ApplicationStatus.QUEUED, reason="Advance for preparation")
        elif app.status == ApplicationStatus.MATCHED:
            app = await self._app_svc.transition(db, application_id, ApplicationStatus.QUEUED, reason="Advance for preparation")
        elif app.status != ApplicationStatus.QUEUED:
            status_name = app.status.value if hasattr(app.status, "value") else str(app.status)
            raise ValueError(
                f"Application is in '{status_name}' state. Only queued, matched, or previously withdrawn/failed applications can be prepared."
            )

        user: User = app.user
        if not user:
            raise ValueError("Application has no associated user")

        user_profile = self._build_user_profile(user)

        # ── 2. Load resume ────────────────────────────────────────────────────
        import os
        resume: Optional[Resume] = app.resume
        if not resume and user.resumes:
            resume = next((r for r in user.resumes if r.is_default), user.resumes[0])

        resume_path: Optional[str] = None
        if resume and resume.file_path and os.path.exists(resume.file_path):
            resume_path = os.path.abspath(resume.file_path)

        # ── 3. Check daily limit ──────────────────────────────────────────────
        try:
            await self._app_svc.enforce_daily_limit(db, user.id)
        except DailyLimitReachedError:
            await self._app_svc.transition(
                db, application_id, ApplicationStatus.FAILED,
                reason="Daily application limit reached"
            )
            await db.commit()
            return await self._app_svc.get_by_id(db, application_id)

        # ── 4. Transition to PREPARING ─────────────────────────────────────────
        app = await self._app_svc.transition(
            db, application_id, ApplicationStatus.PREPARING,
            reason="Browser automation starting"
        )
        await db.commit()

        # ── 5. Create attempt record ──────────────────────────────────────────
        attempt = ApplicationAttempt(
            application_id=application_id,
            attempt_number=app.attempt_count,
            status=AttemptStatus.STARTED,
            started_at=datetime.now(timezone.utc),
        )
        db.add(attempt)
        await db.flush()

        # ── 6. Run browser engine ─────────────────────────────────────────────
        url = (
            app.application_url
            or (app.job.application_url if app.job else None)
            or (app.job.canonical_url if app.job else None)
        )
        if url and not app.application_url:
            app.application_url = url
            await db.flush()

        if not url:
            return await self._fail_application(
                db, app, attempt, "no_url",
                "Application has no URL — cannot open browser"
            )

        is_test_run = app.is_test_run
        auto_apply_mode = app.auto_apply_mode or "safe"
        if force_submit:
            is_test_run = False
            auto_apply_mode = "auto"

        ai_provider = None
        try:
            ai_provider = get_ai_provider()
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                "AI provider unavailable, profile-only mode: %s", exc
            )

        engine = BrowserEngine()
        try:
            engine_result = await engine.apply(
                url=url,
                user_profile=user_profile,
                resume_path=resume_path,
                ai_provider=ai_provider,
                is_test_run=is_test_run,
                auto_apply_mode=auto_apply_mode,
            )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error("BrowserEngine crashed: %s", exc, exc_info=True)
            return await self._fail_application(
                db, app, attempt, "browser_crash", str(exc)[:500]
            )

        # ── 7. Save engine results ────────────────────────────────────────────
        app.detected_fields = engine_result.detected_fields
        app.filled_fields = engine_result.filled_fields
        app.warnings = engine_result.warnings or []
        app.last_error = engine_result.error_message

        attempt.status = AttemptStatus.COMPLETED if engine_result.success else AttemptStatus.FAILED
        attempt.completed_at = datetime.now(timezone.utc)
        attempt.fields_detected = engine_result.fields_detected
        attempt.fields_filled = engine_result.fields_filled
        attempt.questions_detected = engine_result.questions_detected
        attempt.questions_answered = engine_result.answers_generated
        attempt.resume_uploaded = engine_result.resume_uploaded
        attempt.form_validated = engine_result.form_validated
        attempt.would_submit = engine_result.would_submit
        attempt.step_log = engine_result.step_log
        if engine_result.error_type:
            attempt.error_type = engine_result.error_type
            attempt.error_message = engine_result.error_message

        await db.flush()

        if not engine_result.success:
            return await self._fail_application(
                db, app, attempt,
                engine_result.error_type or "unknown",
                engine_result.error_message or "Browser engine failed"
            )

        # ── 8. Handle submission / review ──────────────────────────────────────
        if engine_result.submitted:
            app = await self._app_svc.transition(
                db, application_id, ApplicationStatus.SUBMITTING,
                reason="Browser engine submitting form"
            )
            app = await self._app_svc.transition(
                db, application_id, ApplicationStatus.SUBMITTED,
                reason="Form submitted successfully",
                extra_fields={
                    "confirmation_id": engine_result.confirmation_text or "SUBMITTED"
                }
            )
            await db.commit()
            return app

        # Safe mode / test mode → REVIEW
        app = await self._app_svc.transition(
            db, application_id, ApplicationStatus.REVIEW,
            reason=(
                "Form filled — waiting for user review"
                if engine_result.fields_filled > 0
                else "No fields filled — manual review needed"
            )
        )
        await db.commit()
        return app

    async def submit_after_review(
        self,
        db: AsyncSession,
        application_id: uuid.UUID,
    ) -> Application:
        """Re-open browser and submit after user reviews the filled form."""
        app = await self._app_svc.get_by_id(db, application_id)
        if not app:
            raise ValueError(f"Application {application_id} not found")
        if app.status != ApplicationStatus.REVIEW:
            raise ValueError(f"Application must be in REVIEW state. Current: {app.status}")
        return await self.prepare_and_fill(db, application_id, force_submit=True)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _build_user_profile(self, user: User) -> Dict[str, Any]:
        """Convert User ORM object to flat dict for the form filler."""
        return {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "city": user.city,
            "state": user.state,
            "country": user.country,
            "zip_code": user.zip_code,
            "current_title": user.current_title,
            "current_company": user.current_company,
            "years_of_experience": user.years_of_experience,
            "headline": user.headline,
            "summary": user.summary,
            "linkedin_url": user.linkedin_url,
            "github_url": user.github_url,
            "portfolio_url": user.portfolio_url,
            "website_url": user.website_url,
            "work_authorization": user.work_authorization,
            "requires_sponsorship": user.requires_sponsorship,
            "willing_to_relocate": user.willing_to_relocate,
            "notice_period_days": user.notice_period_days,
            "desired_salary_min": user.desired_salary_min,
            "desired_salary_max": user.desired_salary_max,
            "salary_currency": user.salary_currency or "INR",
            "gender": user.gender,
            "disability_status": user.disability_status,
            "veteran_status": user.veteran_status,
        }

    async def _fail_application(
        self,
        db: AsyncSession,
        app: Application,
        attempt: ApplicationAttempt,
        error_type: str,
        error_message: str,
    ) -> Application:
        attempt.status = AttemptStatus.FAILED
        attempt.error_type = error_type
        attempt.error_message = error_message
        attempt.completed_at = datetime.now(timezone.utc)
        await db.flush()
        app = await self._app_svc.transition(
            db, app.id, ApplicationStatus.FAILED,
            reason=f"{error_type}: {error_message[:200]}"
        )
        await db.commit()
        return app


# ── Browser service singleton ──────────────────────────────────────────────────
browser_application_service = BrowserApplicationService()
