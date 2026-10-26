"""backend/app/api/v1/endpoints/applications.py — Application API endpoints."""
from __future__ import annotations

import uuid
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.core.database import get_db
from app.models.application import ApplicationStatus
from app.models.user import User
from app.schemas.application import (
    ApplicationCreate,
    ApplicationQueueItem,
    ApplicationRead,
    ApplicationReview,
    ApplicationStats,
    ApplicationUpdate,
    AutoApplySettingsCreate,
    AutoApplySettingsRead,
    AutoApplySettingsUpdate,
    DryRunResult,
    StatusTransitionRequest,
)
from app.services.application_service import (
    ApplicationService,
    BrowserApplicationService,
    DailyLimitReachedError,
    DuplicateApplicationError,
    InvalidTransitionError,
    application_service,
    browser_application_service,
)

router = APIRouter(prefix="/applications", tags=["Applications"])


# ── Create ─────────────────────────────────────────────────────────────────────

@router.post("/", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
async def create_application(
    payload: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    """Create a new application in DISCOVERED state."""
    try:
        app = await application_service.create_application(
            db=db,
            user_id=current_user.id,
            job_id=payload.job_id,
            resume_id=payload.resume_id,
            auto_apply_mode=payload.auto_apply_mode or "safe",
        )
        return ApplicationRead.model_validate(app)
    except DuplicateApplicationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


# ── Queue ──────────────────────────────────────────────────────────────────────

@router.get("/queue", response_model=List[ApplicationQueueItem])
async def get_queue(
    current_user: User = Depends(get_current_user),
    status: Optional[str] = Query(None, description="Optional status filter"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> List[ApplicationQueueItem]:
    """Return the active application queue for the user."""
    return await application_service.get_queue(
        db, current_user.id, status_filter=status, limit=limit, offset=offset
    )


# ── Stats ──────────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=ApplicationStats)
async def get_stats(
    current_user: User = Depends(get_current_user),
    target_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> ApplicationStats:
    """Return daily application statistics."""
    return await application_service.get_stats(db, current_user.id, target_date)


# ── Dry run ────────────────────────────────────────────────────────────────────

@router.post("/test", response_model=DryRunResult)
async def dry_run(
    job_id: uuid.UUID = Query(...),
    resume_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DryRunResult:
    """
    Open the job application page in browser (test mode), detect + fill form,
    but NEVER submit. Returns detected fields and fill summary.
    """
    try:
        from app.models.job import Job
        from app.browser.browser_engine import BrowserEngine
        from app.ai.factory import get_ai_provider
        from app.models.user import User as UserModel
        import os

        job = await db.get(Job, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        # Build user profile
        from app.services.application_service import BrowserApplicationService
        svc = BrowserApplicationService()
        user = await db.get(UserModel, current_user.id)
        user_profile = svc._build_user_profile(user)

        # Get resume path
        resume_path = None
        if resume_id:
            from app.models.resume import Resume
            resume = await db.get(Resume, resume_id)
            if resume and resume.file_path and os.path.exists(resume.file_path):
                resume_path = os.path.abspath(resume.file_path)

        # Run browser engine in test mode
        ai_provider = None
        try:
            ai_provider = get_ai_provider()
        except Exception:
            pass

        engine = BrowserEngine()
        result = await engine.apply(
            url=job.application_url or "",
            user_profile=user_profile,
            resume_path=resume_path,
            ai_provider=ai_provider,
            is_test_run=True,
            auto_apply_mode="safe",
        )

        return DryRunResult(
            job_id=job_id,
            application_url=job.application_url,
            application_method=job.application_method.value if job.application_method else None,
            fields_detected=result.fields_detected,
            fields_filled=result.fields_filled,
            questions_detected=result.questions_detected,
            answers_generated=result.answers_generated,
            resume_uploaded=result.resume_uploaded,
            would_submit=False,
            warnings=result.warnings,
            errors=[result.error_message] if result.error_message else [],
            is_test_run=True,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dry run failed: {str(e)[:300]}"
        )


# ── Single application ─────────────────────────────────────────────────────────

@router.get("/{application_id}", response_model=ApplicationRead)
async def get_application(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    app = await application_service.get_by_id_full(db, application_id)
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return ApplicationRead.model_validate(app)


@router.get("/{application_id}/review", response_model=ApplicationReview)
async def get_review(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ApplicationReview:
    """Return the full review packet for user confirmation before submission."""
    try:
        return await application_service.get_review(db, application_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── State transitions ──────────────────────────────────────────────────────────

@router.post("/{application_id}/prepare", response_model=ApplicationRead)
async def prepare_application(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplicationRead:
    """
    Launch browser automation: navigate to job page, detect form fields,
    fill them from user profile + AI, save results, move to REVIEW.
    
    In test_run mode (default) the form is filled but NOT submitted.
    Set AUTO_APPLY_TEST_MODE=false and auto_apply_mode=auto to enable real submission.
    """
    try:
        app = await browser_application_service.prepare_and_fill(
            db=db,
            application_id=application_id,
        )
        full_app = await application_service.get_by_id_full(db, application_id)
        return ApplicationRead.model_validate(full_app or app)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Browser automation failed: {str(e)[:300]}"
        )


@router.post("/{application_id}/submit", response_model=ApplicationRead)
async def submit_application(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplicationRead:
    """
    After user reviews the filled form, re-open browser and submit.
    Only works when the application is in REVIEW state.
    
    WARNING: This performs a REAL submission unless AUTO_APPLY_TEST_MODE=true.
    """
    try:
        app = await browser_application_service.submit_after_review(
            db=db,
            application_id=application_id,
        )
        full_app = await application_service.get_by_id_full(db, application_id)
        return ApplicationRead.model_validate(full_app or app)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Browser submission failed: {str(e)[:300]}"
        )


@router.post("/{application_id}/cancel", response_model=ApplicationRead)
async def cancel_application(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    """Withdraw an application."""
    try:
        app = await application_service.cancel(db, application_id)
        await db.commit()
        return ApplicationRead.model_validate(app)
    except (ValueError, InvalidTransitionError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cancellation failed: {str(e)[:300]}"
        )


@router.post("/{application_id}/retry", response_model=ApplicationRead)
async def retry_application(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    """Re-queue a failed application (max 3 retries)."""
    try:
        app = await application_service.retry(db, application_id)
        await db.commit()
        return ApplicationRead.model_validate(app)
    except (ValueError, InvalidTransitionError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retry failed: {str(e)[:300]}"
        )


@router.post("/{application_id}/transition", response_model=ApplicationRead)
async def manual_transition(
    application_id: uuid.UUID,
    payload: StatusTransitionRequest,
    db: AsyncSession = Depends(get_db),
) -> ApplicationRead:
    """Generic state transition endpoint (for testing and admin use)."""
    try:
        app = await application_service.transition(
            db, application_id, payload.new_status, payload.reason
        )
        return ApplicationRead.model_validate(app)
    except (ValueError, InvalidTransitionError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Attempt log ────────────────────────────────────────────────────────────────

@router.get("/{application_id}/attempts")
async def get_attempt_log(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list:
    """
    Return the step-by-step browser automation log for all attempts.
    Useful for debugging what happened during form fill.
    """
    from sqlalchemy import select
    from app.models.application import ApplicationAttempt
    result = await db.execute(
        select(ApplicationAttempt)
        .where(ApplicationAttempt.application_id == application_id)
        .order_by(ApplicationAttempt.created_at)
    )
    attempts = result.scalars().all()
    return [
        {
            "attempt_number": a.attempt_number,
            "status": a.status,
            "started_at": a.started_at.isoformat() if a.started_at else None,
            "completed_at": a.completed_at.isoformat() if a.completed_at else None,
            "fields_detected": a.fields_detected,
            "fields_filled": a.fields_filled,
            "resume_uploaded": a.resume_uploaded,
            "form_validated": a.form_validated,
            "error_type": a.error_type,
            "error_message": a.error_message,
            "step_log": a.step_log or [],
        }
        for a in attempts
    ]

