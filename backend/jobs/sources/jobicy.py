"""
backend/jobs/sources/jobicy.py

Jobicy Remote Job Search API source.
Fetches global engineering and programming remote jobs.
Free open REST API — no API key required!
API docs: https://jobicy.com/jobs-rss-feed
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

_BASE_URL = "https://jobicy.com/api/v2/remote-jobs"
_TIMEOUT = 12.0


class JobicySource(JobSourceBase):
    """
    Fetches remote jobs from Jobicy across software engineering, devops, and data domains.
    """

    @property
    def source_name(self) -> str:
        return "jobicy"

    @property
    def is_configured(self) -> bool:
        return True

    async def search_jobs(self, criteria: SearchCriteria) -> List[NormalizedJob]:
        keywords = criteria.get("keywords", [])
        search_kw = keywords[0] if keywords else ""
        location_filter = (criteria.get("location") or "").lower()

        params: Dict[str, Any] = {"count": 40}
        if search_kw:
            params["tag"] = search_kw

        headers = {
            "User-Agent": "JobApplyBot/1.0 (https://github.com/job-apply-bot; contact@jobapplybot.org)",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
                resp = await client.get(_BASE_URL, params=params, headers=headers)
                if resp.status_code != 200:
                    logger.warning("Jobicy API returned HTTP %s", resp.status_code)
                    return []
                data = resp.json()
        except Exception as exc:
            logger.warning("Jobicy fetch failed: %s", exc)
            return []

        raw_jobs = data.get("jobs", [])
        results: List[NormalizedJob] = []

        for item in raw_jobs:
            title = item.get("jobTitle") or ""
            geo = item.get("jobGeo") or "Remote Worldwide"
            desc = item.get("jobDescription") or item.get("jobExcerpt") or ""

            if location_filter and location_filter not in ("remote", "any", "worldwide", "all"):
                if location_filter not in geo.lower() and "world" not in geo.lower():
                    continue

            posted_at = None
            pub_date = item.get("pubDate")
            if pub_date:
                try:
                    posted_at = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                except Exception:
                    pass

            industry_val = item.get("jobIndustry") or []
            if isinstance(industry_val, list):
                skills = [str(s).strip() for s in industry_val if str(s).strip()]
            else:
                skills = [str(s).strip() for s in str(industry_val).split(",") if str(s).strip()]

            job: NormalizedJob = {
                "external_id": f"jobicy_{item.get('id')}",
                "source": "jobicy",
                "title": title or "Software Engineer",
                "company_name": item.get("companyName") or "Tech Employer",
                "description": desc,
                "canonical_url": item.get("url"),
                "apply_url": item.get("url"),
                "location": geo,
                "is_remote": True,
                "is_hybrid": False,
                "work_mode": "remote",
                "employment_type": item.get("jobType") or "full-time",
                "required_skills": skills,
                "posted_at": posted_at,
                "discovered_at": datetime.now(timezone.utc),
                "raw_data": {"id": item.get("id"), "source": "jobicy"},
            }
            results.append(job)

        logger.info("Jobicy returned %d jobs", len(results))
        return results
