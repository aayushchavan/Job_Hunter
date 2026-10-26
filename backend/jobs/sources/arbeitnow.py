"""
backend/jobs/sources/arbeitnow.py

Arbeitnow Job Search API source.
Fetches tech and software development jobs from Europe, US, and Remote.
Free open REST API — no API key required!
API docs: https://www.arbeitnow.com/api/job-board-api
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from jobs.sources.base import (
    JobSourceBase,
    NormalizedJob,
    SearchCriteria,
)

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.arbeitnow.com/api/job-board-api"
_TIMEOUT = 12.0


class ArbeitnowSource(JobSourceBase):
    """
    Fetches engineering and tech jobs from Arbeitnow across US, EU, and Remote worldwide.
    """

    @property
    def source_name(self) -> str:
        return "arbeitnow"

    @property
    def is_configured(self) -> bool:
        return True

    async def search_jobs(self, criteria: SearchCriteria) -> List[NormalizedJob]:
        keywords = [k.lower() for k in criteria.get("keywords", [])]
        location_filter = (criteria.get("location") or "").lower()
        remote_only = criteria.get("remote", False)

        headers = {
            "User-Agent": "JobApplyBot/1.0 (https://github.com/job-apply-bot; contact@jobapplybot.org)",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
                resp = await client.get(_BASE_URL, headers=headers)
                if resp.status_code != 200:
                    logger.warning("Arbeitnow API returned HTTP %s", resp.status_code)
                    return []
                data = resp.json()
        except Exception as exc:
            logger.warning("Arbeitnow fetch failed: %s", exc)
            return []

        raw_jobs = data.get("data", [])
        results: List[NormalizedJob] = []

        for item in raw_jobs:
            title = item.get("title") or ""
            desc = item.get("description") or ""
            tags = item.get("tags") or []
            loc = item.get("location") or "Remote / Europe"
            is_remote = bool(item.get("remote", False)) or "remote" in loc.lower()

            if remote_only and not is_remote:
                continue

            if location_filter and location_filter not in loc.lower() and not is_remote:
                continue

            # Match keywords if provided
            if keywords:
                full_text = f"{title} {desc} {' '.join(tags)}".lower()
                if not any(kw in full_text for kw in keywords):
                    continue

            posted_at = None
            created_ts = item.get("created_at")
            if created_ts:
                try:
                    posted_at = datetime.fromtimestamp(created_ts, tz=timezone.utc)
                except Exception:
                    pass

            job: NormalizedJob = {
                "external_id": f"arbeitnow_{item.get('slug') or item.get('id')}",
                "source": "arbeitnow",
                "title": title or "Software Engineer",
                "company_name": item.get("company_name") or "Tech Employer",
                "description": desc,
                "canonical_url": item.get("url"),
                "apply_url": item.get("url"),
                "location": loc,
                "is_remote": is_remote,
                "is_hybrid": False,
                "work_mode": "remote" if is_remote else "onsite",
                "employment_type": "full-time",
                "required_skills": tags,
                "posted_at": posted_at,
                "discovered_at": datetime.now(timezone.utc),
                "raw_data": {"slug": item.get("slug"), "source": "arbeitnow"},
            }
            results.append(job)

            if len(results) >= 30:
                break

        logger.info("Arbeitnow returned %d matching jobs", len(results))
        return results
