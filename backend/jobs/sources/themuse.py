"""
backend/jobs/sources/themuse.py

The Muse Job Search API source.
Fetches top enterprise & high-growth tech company job postings worldwide.
Free open REST API — no API key required!
API docs: https://www.themuse.com/developers/api/v2
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

_BASE_URL = "https://www.themuse.com/api/public/jobs"
_TIMEOUT = 12.0


class TheMuseSource(JobSourceBase):
    """
    Fetches job listings from The Muse for tech and engineering positions.
    """

    @property
    def source_name(self) -> str:
        return "themuse"

    @property
    def is_configured(self) -> bool:
        return True

    async def search_jobs(self, criteria: SearchCriteria) -> List[NormalizedJob]:
        keywords = [k.lower() for k in criteria.get("keywords", [])]
        location_filter = (criteria.get("location") or "").lower()
        page = criteria.get("page", 1)

        params: Dict[str, Any] = {
            "page": max(1, page),
            "category": "Software Engineering",
        }
        if location_filter and "remote" not in location_filter:
            params["location"] = location_filter

        headers = {
            "User-Agent": "JobApplyBot/1.0 (https://github.com/job-apply-bot; contact@jobapplybot.org)",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
                resp = await client.get(_BASE_URL, params=params, headers=headers)
                if resp.status_code != 200:
                    logger.warning("The Muse API returned HTTP %s", resp.status_code)
                    return []
                data = resp.json()
        except Exception as exc:
            logger.warning("The Muse fetch failed: %s", exc)
            return []

        raw_jobs = data.get("results", [])
        results: List[NormalizedJob] = []

        for item in raw_jobs:
            title = item.get("name") or ""
            company_obj = item.get("company") or {}
            comp_name = company_obj.get("name") or "Leading Company"
            desc = item.get("contents") or ""

            loc_names = [l.get("name", "") for l in item.get("locations", []) if l.get("name")]
            loc_str = ", ".join(loc_names) if loc_names else "Various Locations"
            is_remote = any("remote" in l.lower() or "flexible" in l.lower() for l in loc_names)

            # Match keywords if specified
            if keywords:
                full_text = f"{title} {desc} {comp_name}".lower()
                if not any(kw in full_text for kw in keywords):
                    continue

            posted_at = None
            pub_date = item.get("publication_date")
            if pub_date:
                try:
                    posted_at = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                except Exception:
                    pass

            landing_page = item.get("refs", {}).get("landing_page") or ""

            cats = [c.get("name", "") for c in item.get("categories", [])]
            levels = [lvl.get("name", "") for lvl in item.get("levels", [])]

            job: NormalizedJob = {
                "external_id": f"themuse_{item.get('id')}",
                "source": "themuse",
                "title": title or "Software Engineer",
                "company_name": comp_name,
                "description": desc,
                "canonical_url": landing_page,
                "apply_url": landing_page,
                "location": loc_str,
                "is_remote": is_remote,
                "is_hybrid": False,
                "work_mode": "remote" if is_remote else "onsite",
                "employment_type": "full-time",
                "required_skills": cats + levels,
                "posted_at": posted_at,
                "discovered_at": datetime.now(timezone.utc),
                "raw_data": {"id": item.get("id"), "source": "themuse"},
            }
            results.append(job)

        logger.info("The Muse returned %d jobs", len(results))
        return results
