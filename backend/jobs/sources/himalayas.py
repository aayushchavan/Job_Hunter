"""
backend/jobs/sources/himalayas.py

Himalayas Remote Job Search API source.
Fetches high-quality remote engineering and developer jobs worldwide.
Free open REST API — no API key required!
API docs: https://himalayas.app/jobs/api
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

_BASE_URL = "https://himalayas.app/jobs/api"
_TIMEOUT = 12.0


class HimalayasSource(JobSourceBase):
    """
    Fetches remote jobs from Himalayas across worldwide software companies.
    """

    @property
    def source_name(self) -> str:
        return "himalayas"

    @property
    def is_configured(self) -> bool:
        return True

    async def search_jobs(self, criteria: SearchCriteria) -> List[NormalizedJob]:
        keywords = [k.lower() for k in criteria.get("keywords", [])]
        location_filter = (criteria.get("location") or "").lower()

        headers = {
            "User-Agent": "JobApplyBot/1.0 (https://github.com/job-apply-bot; contact@jobapplybot.org)",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
                resp = await client.get(f"{_BASE_URL}?limit=50", headers=headers)
                if resp.status_code != 200:
                    logger.warning("Himalayas API returned HTTP %s", resp.status_code)
                    return []
                data = resp.json()
        except Exception as exc:
            logger.warning("Himalayas fetch failed: %s", exc)
            return []

        raw_jobs = data.get("jobs", [])
        results: List[NormalizedJob] = []

        for item in raw_jobs:
            title = item.get("title") or ""
            desc = item.get("description") or ""
            cats = item.get("categories") or []
            locs = item.get("locationRestrictions") or []
            loc_str = ", ".join(locs) if locs else "Remote Worldwide"

            if location_filter and location_filter not in ("remote", "any", "worldwide", "all"):
                if location_filter not in loc_str.lower() and "world" not in loc_str.lower():
                    continue

            # Filter by keywords if provided
            if keywords:
                full_text = f"{title} {desc} {' '.join(cats)}".lower()
                if not any(kw in full_text for kw in keywords):
                    continue

            # Parse date
            posted_at = None
            date_str = item.get("pubDate") or item.get("publishedAt")
            if date_str:
                try:
                    posted_at = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                except Exception:
                    pass

            slug = item.get("slug") or f"{item.get('companyName')}_{title}".replace(" ", "_")

            job: NormalizedJob = {
                "external_id": f"himalayas_{slug}",
                "source": "himalayas",
                "title": title or "Software Engineer",
                "company_name": item.get("companyName") or "Remote Company",
                "description": desc,
                "canonical_url": item.get("applicationLink"),
                "apply_url": item.get("applicationLink"),
                "location": loc_str,
                "is_remote": True,
                "is_hybrid": False,
                "work_mode": "remote",
                "employment_type": "full-time",
                "required_skills": [c.replace("-", " ") for c in cats[:8]],
                "salary_min": item.get("minSalary"),
                "salary_max": item.get("maxSalary"),
                "salary_currency": "USD" if (item.get("minSalary") or item.get("maxSalary")) else None,
                "posted_at": posted_at,
                "discovered_at": datetime.now(timezone.utc),
                "raw_data": {"slug": slug, "source": "himalayas"},
            }
            results.append(job)

            if len(results) >= 30:
                break

        logger.info("Himalayas returned %d matching jobs", len(results))
        return results
