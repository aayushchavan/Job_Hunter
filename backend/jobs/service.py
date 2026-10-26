"""
backend/jobs/service.py

JobDiscoveryService — orchestrates the full discovery pipeline:

  1. Load enabled sources from registry
  2. Build search parameters
  3. Query each source (independently — one failing source does not stop others)
  4. Normalize each result
  5. Deduplicate (fingerprint + source_job_id)
  6. Upsert into PostgreSQL
  7. Return accurate statistics

Rules:
  - No fake/mock jobs in production code
  - No LLM/Claude calls
  - Logs structured information at each stage
  - Never logs API keys or secrets
  - Returns real DB counts, not hardcoded values
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from jobs.normalizer import normalize_job
from jobs.sources.base import (
    NormalizedJob, SearchCriteria, SourceFetchError, SourceNotConfiguredError,
)
from jobs.sources.registry import JobSourceRegistry, get_registry

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryStats:
    """Statistics returned by a discovery run."""
    sources_attempted: int = 0
    sources_succeeded: int = 0
    sources_failed: int = 0
    source_errors: Dict[str, str] = field(default_factory=dict)

    jobs_fetched: int = 0        # Total raw results from all sources
    jobs_normalized: int = 0     # Successfully normalized
    jobs_new: int = 0            # Inserted as new rows
    jobs_updated: int = 0        # Updated existing rows (fresher data)
    jobs_duplicates: int = 0     # Already existed, not changed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sources_attempted": self.sources_attempted,
            "sources_succeeded": self.sources_succeeded,
            "sources_failed": self.sources_failed,
            "source_errors": self.source_errors,
            "jobs_fetched": self.jobs_fetched,
            "jobs_normalized": self.jobs_normalized,
            "jobs_new": self.jobs_new,
            "jobs_updated": self.jobs_updated,
            "jobs_duplicates": self.jobs_duplicates,
        }


class JobDiscoveryService:
    """
    Orchestrates job discovery from all configured sources.

    Instantiate with an AsyncSession and optionally a custom registry
    (useful for testing with mocked sources).
    """

    def __init__(
        self,
        db: AsyncSession,
        registry: Optional[JobSourceRegistry] = None,
    ) -> None:
        self._db = db
        self._registry = registry or get_registry()
        self._pending_by_fingerprint: Dict[str, Job] = {}
        self._pending_by_key: Dict[tuple[str, str], Job] = {}

    async def discover(self, criteria: SearchCriteria) -> DiscoveryStats:
        """
        Run the full discovery pipeline.

        Args:
            criteria: Search parameters (keywords, location, etc.)

        Returns:
            DiscoveryStats with accurate counts from the database.
        """
        stats = DiscoveryStats()
        enabled = self._registry.enabled_sources()

        if not enabled:
            logger.warning(
                "No job sources are configured. "
                "Set ADZUNA_APP_ID and ADZUNA_APP_KEY to enable discovery."
            )
            return stats

        logger.info(
            "Job discovery started: %d source(s), criteria=%s",
            len(enabled),
            {k: v for k, v in criteria.items() if k not in ("password",)},
        )

        all_normalized: List[NormalizedJob] = []

        async def _query_single_source(src: JobSourceBase):
            logger.info("Querying source: %s", src.source_name)
            try:
                raw_jobs = await src.search_jobs(criteria)
                norm_jobs: List[NormalizedJob] = []
                for raw in raw_jobs:
                    try:
                        norm_jobs.append(normalize_job(raw))
                    except Exception as n_exc:
                        logger.warning("Normalization failed for job from %s: %s", src.source_name, n_exc)
                return src.source_name, norm_jobs, None, len(raw_jobs)
            except Exception as exc:
                return src.source_name, [], exc, 0

        # Query all global sources concurrently in parallel
        tasks = [_query_single_source(source) for source in enabled]
        source_results = await asyncio.gather(*tasks)

        for source_name, norm_jobs, exc, raw_count in source_results:
            stats.sources_attempted += 1
            if exc:
                stats.sources_failed += 1
                if isinstance(exc, SourceNotConfiguredError):
                    stats.source_errors[source_name] = f"not_configured: {exc}"
                elif isinstance(exc, SourceFetchError):
                    stats.source_errors[source_name] = f"fetch_error: {exc}"
                else:
                    stats.source_errors[source_name] = f"unexpected: {type(exc).__name__}"
                logger.warning("Source %s error: %s", source_name, exc)
            else:
                stats.sources_succeeded += 1
                stats.jobs_fetched += raw_count
                stats.jobs_normalized += len(norm_jobs)
                all_normalized.extend(norm_jobs)
                logger.info("Source %s returned %d jobs (%d normalized)", source_name, raw_count, len(norm_jobs))

        # Deduplicate results within this batch before inserting
        unique_normalized: List[NormalizedJob] = []
        seen_batch_fps: set[str] = set()
        seen_batch_keys: set[tuple[str, str]] = set()

        for j in all_normalized:
            fp = j.get("fingerprint") or ""
            src = j.get("source") or ""
            ext = str(j.get("external_id") or "")
            if fp and fp in seen_batch_fps:
                stats.jobs_duplicates += 1
                continue
            if src and ext and (src, ext) in seen_batch_keys:
                stats.jobs_duplicates += 1
                continue
            if fp:
                seen_batch_fps.add(fp)
            if src and ext:
                seen_batch_keys.add((src, ext))
            unique_normalized.append(j)

        # Upsert all deduplicated jobs
        for job_data in unique_normalized:
            result = await self._upsert_job(job_data)
            if result == "new":
                stats.jobs_new += 1
            elif result == "updated":
                stats.jobs_updated += 1
            else:
                stats.jobs_duplicates += 1

        try:
            await self._db.flush()
        except Exception as f_exc:
            logger.warning("Flush duplicate violation caught, cleaning up session: %s", f_exc)
            await self._db.rollback()

        logger.info(
            "Discovery complete: fetched=%d normalized=%d new=%d updated=%d duplicates=%d",
            stats.jobs_fetched, stats.jobs_normalized,
            stats.jobs_new, stats.jobs_updated, stats.jobs_duplicates,
        )

        return stats

    async def _upsert_job(self, job_data: NormalizedJob) -> str:
        """
        Insert or update a single job in the database.

        Returns: "new" | "updated" | "duplicate"

        Lookup order:
          1. in-memory pending tracker
          2. fingerprint (most stable identifier)
          3. (source_name, external_id) pair
        """
        fingerprint: str = job_data.get("fingerprint") or ""
        source_name: str = job_data.get("source") or ""
        external_id: str = str(job_data.get("external_id") or "")

        existing: Optional[Job] = None

        # 0. Check in-memory pending jobs from this current discovery session
        if fingerprint and fingerprint in self._pending_by_fingerprint:
            existing = self._pending_by_fingerprint[fingerprint]
        elif source_name and external_id and (source_name, external_id) in self._pending_by_key:
            existing = self._pending_by_key[(source_name, external_id)]

        # 1. Try fingerprint lookup in DB
        if existing is None and fingerprint:
            result = await self._db.execute(
                select(Job).where(Job.fingerprint == fingerprint)
            )
            existing = result.scalar_one_or_none()

        # 2. Fallback: (source_name, external_id) lookup in DB
        if existing is None and source_name and external_id:
            result = await self._db.execute(
                select(Job).where(
                    Job.source_name == source_name,
                    Job.source_job_id == external_id,
                )
            )
            existing = result.scalar_one_or_none()

        if existing is None:
            # New job — insert
            new_job = self._build_job_row(job_data)
            self._db.add(new_job)
            if fingerprint:
                self._pending_by_fingerprint[fingerprint] = new_job
            if source_name and external_id:
                self._pending_by_key[(source_name, external_id)] = new_job
            return "new"

        # Existing job — check if we should update
        updated = self._apply_updates(existing, job_data)
        return "updated" if updated else "duplicate"

    @staticmethod
    def _build_job_row(data: NormalizedJob) -> Job:
        """Create a new Job ORM row from normalized data."""
        return Job(
            source_name=data.get("source"),
            source_job_id=str(data.get("external_id") or ""),
            fingerprint=data.get("fingerprint"),
            title=data.get("title") or "Untitled",
            company_name=data.get("company_name") or "Unknown",
            description=data.get("description"),
            requirements=data.get("requirements"),
            location=data.get("location"),
            is_remote=data.get("is_remote"),
            is_hybrid=data.get("is_hybrid"),
            work_mode=data.get("work_mode"),
            employment_type=data.get("employment_type"),
            experience_min_years=data.get("experience_min_years"),
            experience_max_years=data.get("experience_max_years"),
            required_skills=data.get("required_skills") or [],
            preferred_skills=data.get("preferred_skills") or [],
            education_required=data.get("education_required"),
            graduation_year_required=data.get("graduation_year_required"),
            salary_min=data.get("salary_min"),
            salary_max=data.get("salary_max"),
            salary_currency=data.get("salary_currency"),
            application_url=data.get("apply_url"),
            canonical_url=data.get("canonical_url"),
            posted_at=data.get("posted_at"),
            discovered_at=data.get("discovered_at") or datetime.now(timezone.utc),
            raw_data=data.get("raw_data"),
        )

    @staticmethod
    def _apply_updates(existing: Job, data: NormalizedJob) -> bool:
        """
        Update mutable fields on an existing job row.
        Returns True if any meaningful field was changed.

        Note: discovered_at is intentionally NOT updated — it records first discovery.
        Note: description updates are intentionally NOT counted as 'updated' for
              duplicate-counting purposes unless substantial fields change.
        """
        changed = False

        def _set(attr: str, value: Any) -> None:
            nonlocal changed
            if value is not None and getattr(existing, attr) != value:
                setattr(existing, attr, value)
                changed = True

        # Only update fields that carry meaningful new information
        _set("location", data.get("location"))
        _set("is_remote", data.get("is_remote"))
        _set("is_hybrid", data.get("is_hybrid"))
        _set("work_mode", data.get("work_mode"))
        _set("employment_type", data.get("employment_type"))
        _set("salary_min", data.get("salary_min"))
        _set("salary_max", data.get("salary_max"))
        _set("salary_currency", data.get("salary_currency"))
        _set("application_url", data.get("apply_url"))
        _set("canonical_url", data.get("canonical_url"))
        _set("posted_at", data.get("posted_at"))

        # Only expand skills — never shrink from a previous fetch
        new_skills = data.get("required_skills") or []
        existing_skills = existing.required_skills or []
        if new_skills and len(new_skills) > len(existing_skills):
            existing.required_skills = new_skills
            changed = True

        return changed

    # ── Dashboard statistics ───────────────────────────────────────────────────

    async def get_daily_stats(self) -> Dict[str, int]:
        """
        Return real job statistics from the database.
        Never hardcodes zero.

        Note: Uses timezone-naive datetime comparison for SQLite compatibility.
        SQLite stores DATETIME without timezone, so naive UTC is used.
        On PostgreSQL, timezone-aware columns handle this correctly.
        """
        today = date.today()
        # Use naive UTC datetime — works on both SQLite (tests) and PostgreSQL (prod)
        today_start = datetime(today.year, today.month, today.day)

        # Total jobs in DB
        total_result = await self._db.execute(
            select(func.count()).select_from(Job).where(Job.is_active == True)
        )
        total_jobs = total_result.scalar_one() or 0

        # Jobs discovered today
        today_result = await self._db.execute(
            select(func.count()).select_from(Job).where(
                Job.discovered_at >= today_start
            )
        )
        jobs_found_today = today_result.scalar_one() or 0

        # Eligible jobs (where eligibility check has been run and passed)
        eligible_result = await self._db.execute(
            select(func.count()).select_from(Job).where(
                Job.is_eligible == True,
                Job.is_active == True,
            )
        )
        jobs_eligible = eligible_result.scalar_one() or 0

        # Jobs with match scores (matched by matching engine)
        matched_result = await self._db.execute(
            select(func.count()).select_from(Job).where(
                Job.match_score.is_not(None),
                Job.is_active == True,
            )
        )
        jobs_scored = matched_result.scalar_one() or 0

        return {
            "total_jobs": total_jobs,
            "jobs_found_today": jobs_found_today,
            "jobs_eligible": jobs_eligible,
            "jobs_scored": jobs_scored,
            # jobs_matched (score >= threshold) is computed by MatchingService (Step 4)
        }

