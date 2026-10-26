"""
backend/jobs/sources/remotive.py

Remotive Remote Job Search API source.
Fetches worldwide tech, software engineering, and developer jobs.
Free open REST API — no API key required!
API docs: https://remotive.com/api/remote-jobs
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from jobs.sources.base import (
    JobSourceBase,
    NormalizedJob,
    SearchCriteria,
    SourceFetchError,
)

logger = logging.getLogger(__name__)

_BASE_URL = "https://remotive.com/api/remote-jobs"
_TIMEOUT = 12.0


class RemotiveSource(JobSourceBase):
    """
    Fetches remote jobs from the Remotive API worldwide.
    Requires no API keys and provides rich real-world listings.
    """

    @property
    def source_name(self) -> str:
        return "remotive"

    @property
    def is_configured(self) -> bool:
        return True

    async def search_jobs(self, criteria: SearchCriteria) -> List[NormalizedJob]:
        keywords = criteria.get("keywords", [])
        search_query = " ".join(keywords) if keywords else ""
        location_filter = (criteria.get("location") or "").lower()

        params: Dict[str, Any] = {"limit": 40}
        if search_query:
            params["search"] = search_query

        headers = {
            "User-Agent": "JobApplyBot/1.0 (https://github.com/job-apply-bot; contact@jobapplybot.org)",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
                resp = await client.get(_BASE_URL, params=params, headers=headers)
                if resp.status_code != 200:
                    logger.warning("Remotive API returned HTTP %s", resp.status_code)
                    return []
                data = resp.json()
        except Exception as exc:
            logger.warning("Remotive fetch failed: %s", exc)
            return []

        raw_jobs = data.get("jobs", [])
        results: List[NormalizedJob] = []

        for item in raw_jobs:
            req_loc = item.get("candidate_required_location") or "Worldwide"
            # Optional location filter
            if location_filter and location_filter not in req_loc.lower() and "world" not in req_loc.lower():
                continue

            # Parse salary
            sal_min, sal_max, sal_curr = self._parse_salary(item.get("salary"))

            # Parse date
            posted_at = None
            pub_date_str = item.get("publication_date")
            if pub_date_str:
                try:
                    posted_at = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
                except Exception:
                    pass

            job: NormalizedJob = {
                "external_id": f"remotive_{item.get('id')}",
                "source": "remotive",
                "title": item.get("title") or "Software Engineer",
                "company_name": item.get("company_name") or "Tech Company",
                "description": item.get("description", ""),
                "canonical_url": item.get("url"),
                "apply_url": item.get("url"),
                "location": req_loc,
                "is_remote": True,
                "is_hybrid": False,
                "work_mode": "remote",
                "employment_type": self._map_employment_type(item.get("job_type")),
                "required_skills": item.get("tags") or [],
                "salary_min": sal_min,
                "salary_max": sal_max,
                "salary_currency": sal_curr,
                "posted_at": posted_at,
                "discovered_at": datetime.now(timezone.utc),
                "raw_data": {"id": item.get("id"), "source": "remotive"},
            }
            results.append(job)

        logger.info("Remotive returned %d jobs for query '%s'", len(results), search_query)
        return results

    def _map_employment_type(self, raw_type: Optional[str]) -> str:
        if not raw_type:
            return "full-time"
        lower = raw_type.lower()
        if "contract" in lower or "freelance" in lower:
            return "contract"
        if "part" in lower:
            return "part-time"
        if "intern" in lower:
            return "internship"
        return "full-time"

    def _parse_salary(self, salary_str: Optional[str]):
        if not salary_str:
            return None, None, None
        nums = [int(n) for n in re.findall(r"\d+", salary_str.replace(",", ""))]
        curr = "USD" if "$" in salary_str else ("EUR" if "€" in salary_str else ("GBP" if "£" in salary_str else "USD"))
        if len(nums) >= 2:
            s_min, s_max = min(nums[0], nums[1]), max(nums[0], nums[1])
            # If numbers are in thousands (e.g. 70 - 80)
            if s_min < 1000:
                s_min *= 1000
            if s_max < 1000:
                s_max *= 1000
            return s_min, s_max, curr
        elif len(nums) == 1:
            val = nums[0]
            if val < 1000:
                val *= 1000
            return val, None, curr
        return None, None, None
