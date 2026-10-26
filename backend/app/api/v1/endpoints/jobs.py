"""
backend/app/api/v1/endpoints/jobs.py

Job discovery and listing API endpoints.

POST /api/v1/jobs/discover  — trigger discovery from configured sources
GET  /api/v1/jobs            — list jobs with pagination and filters
GET  /api/v1/jobs/stats      — real dashboard statistics
GET  /api/v1/jobs/sources    — source configuration status
GET  /api/v1/jobs/{id}       — single job detail

Security:
  - Input validated by Pydantic schemas
  - No user-supplied URLs are navigated to by the backend
  - All external content treated as untrusted data
  - Page size capped at 50
"""
from __future__ import annotations

import logging
import math
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.job import Job
from app.schemas.job import (
    JobDailyStats,
    JobDiscoverRequest,
    JobDiscoverResponse,
    JobListItem,
    JobListResponse,
    JobRead,
    SourceStatus,
    SourceStatusResponse,
)
from jobs.service import JobDiscoveryService, DiscoveryStats
from jobs.sources.registry import get_registry

router = APIRouter(prefix="/jobs", tags=["jobs"])
logger = logging.getLogger(__name__)


# ── POST /jobs/discover ────────────────────────────────────────────────────────

@router.post("/discover", response_model=JobDiscoverResponse, status_code=status.HTTP_200_OK)
async def discover_jobs(
    request: JobDiscoverRequest,
    db: AsyncSession = Depends(get_db),
) -> JobDiscoverResponse:
    """
    Trigger job discovery from all configured sources.

    Builds a SearchCriteria from the request body, queries each enabled source,
    normalizes results, and upserts into the database.

    Returns accurate counts — no hardcoded values.
    """
    criteria = {
        "keywords": request.keywords,
        "location": request.location,
        "country": request.country,
        "remote": request.remote,
        "employment_type": request.employment_type,
        "salary_min": request.salary_min,
        "salary_max": request.salary_max,
        "experience_min_years": request.experience_min_years,
        "experience_max_years": request.experience_max_years,
        "experience_years": request.experience_years,
        "posted_within_days": request.posted_within_days,
        "page": request.page,
        "page_size": request.page_size,
    }

    registry = get_registry()
    enabled = registry.enabled_sources()

    if not enabled:
        return JobDiscoverResponse(
            success=False,
            stats=_empty_stats(),
            message=(
                "No job sources are configured. "
                "Set ADZUNA_APP_ID and ADZUNA_APP_KEY in .env to enable Adzuna discovery."
            ),
        )

    svc = JobDiscoveryService(db=db, registry=registry)

    try:
        stats = await svc.discover(criteria)
        await db.commit()
    except Exception as exc:
        logger.exception("Discovery failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Discovery pipeline error: {type(exc).__name__}: {exc}",
        )

    return JobDiscoverResponse(
        success=True,
        stats=stats.to_dict(),
        message=f"Discovery complete. {stats.jobs_new} new jobs found.",
    )


# ── GET /jobs ─────────────────────────────────────────────────────────────────

@router.get("", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=50, description="Results per page (max 50)"),
    source: Optional[str] = Query(None, description="Filter by source name"),
    company: Optional[str] = Query(None, description="Filter by company name (partial match)"),
    location: Optional[str] = Query(None, description="Filter by location (partial match)"),
    work_mode: Optional[str] = Query(None, description="Filter: remote|hybrid|onsite"),
    employment_type: Optional[str] = Query(None, description="Filter: full-time|part-time|contract"),
    search: Optional[str] = Query(None, description="Search in title, company, description"),
    min_score: Optional[int] = Query(None, description="Filter by minimum match score"),
    is_eligible: Optional[bool] = Query(None, description="Filter by eligibility"),
    experience_min_years: Optional[int] = Query(None, ge=0, description="Filter by minimum experience years"),
    experience_max_years: Optional[int] = Query(None, ge=0, description="Filter by maximum experience years"),
    experience_years: Optional[int] = Query(None, ge=0, description="Filter by target experience years"),
    db: AsyncSession = Depends(get_db),
) -> JobListResponse:
    """
    List discovered jobs with pagination and optional filters.
    Results are ordered by discovered_at descending (newest first).
    """
    query = select(Job).where(Job.is_active == True)

    if source:
        query = query.where(Job.source_name == source)
    if company:
        query = query.where(Job.company_name.ilike(f"%{company}%"))
    if location:
        query = query.where(Job.location.ilike(f"%{location}%"))
    if work_mode:
        query = query.where(Job.work_mode == work_mode.lower())
    if employment_type:
        query = query.where(Job.employment_type == employment_type.lower())
    if min_score is not None:
        query = query.where(Job.match_score >= min_score)
    if search:
        query = query.where(
            or_(
                Job.title.ilike(f"%{search}%"),
                Job.company_name.ilike(f"%{search}%"),
                Job.location.ilike(f"%{search}%"),
                Job.description.ilike(f"%{search}%"),
            )
        )
    if experience_min_years is not None and experience_max_years is not None:
        query = query.where(
            or_(
                Job.experience_min_years.is_(None),
                Job.experience_min_years <= experience_max_years,
            ),
            or_(
                Job.experience_max_years.is_(None),
                Job.experience_max_years >= experience_min_years,
            ),
        )
    elif experience_min_years is not None:
        query = query.where(
            or_(
                Job.experience_max_years >= experience_min_years,
                Job.experience_min_years >= experience_min_years,
                and_(Job.experience_min_years.is_(None), Job.experience_max_years.is_(None)),
            )
        )
    elif experience_max_years is not None:
        query = query.where(
            or_(
                Job.experience_min_years <= experience_max_years,
                Job.experience_min_years.is_(None),
            )
        )
    elif experience_years is not None:
        query = query.where(
            or_(
                Job.experience_min_years.is_(None),
                Job.experience_min_years <= experience_years,
            ),
            or_(
                Job.experience_max_years.is_(None),
                Job.experience_max_years >= experience_years,
            ),
        )
    if is_eligible is not None:
        query = query.where(Job.is_eligible == is_eligible)

    # Total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one() or 0

    # Paginated results
    offset = (page - 1) * page_size
    query = query.order_by(Job.discovered_at.desc().nullsfirst()).offset(offset).limit(page_size)
    result = await db.execute(query)
    jobs = result.scalars().all()

    pages = math.ceil(total / page_size) if total > 0 else 0

    return JobListResponse(
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
        items=[JobListItem.model_validate(j) for j in jobs],
    )


# ── GET /jobs/stats ───────────────────────────────────────────────────────────

@router.get("/stats", response_model=JobDailyStats)
async def get_job_stats(
    db: AsyncSession = Depends(get_db),
) -> JobDailyStats:
    """
    Return real job statistics from the database.
    Values come directly from DB queries — never hardcoded.
    """
    svc = JobDiscoveryService(db=db)
    data = await svc.get_daily_stats()
    return JobDailyStats(**data)


# ── GET /jobs/sources ─────────────────────────────────────────────────────────

@router.get("/sources", response_model=SourceStatusResponse)
async def get_source_statuses() -> SourceStatusResponse:
    """
    Return configuration status for all registered job sources.
    Used by the frontend settings page to show which sources are active.
    """
    registry = get_registry()
    statuses = registry.source_statuses()
    return SourceStatusResponse(
        sources=[
            SourceStatus(
                name=name,
                configured=info["configured"].lower() == "true",
                status=info["status"],
            )
            for name, info in statuses.items()
        ]
    )


# ── GET /jobs/{id} ────────────────────────────────────────────────────────────

@router.get("/{job_id}", response_model=JobRead)
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> JobRead:
    """Return full details for a single job."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobRead.model_validate(job)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _empty_stats():
    from app.schemas.job import DiscoveryStatsSchema
    return DiscoveryStatsSchema(
        sources_attempted=0,
        sources_succeeded=0,
        sources_failed=0,
        jobs_fetched=0,
        jobs_normalized=0,
        jobs_new=0,
        jobs_updated=0,
        jobs_duplicates=0,
    )
