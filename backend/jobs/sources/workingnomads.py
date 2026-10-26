"""
backend/jobs/sources/workingnomads.py

Working Nomads job discovery source.
Queries the public Working Nomads open feed (curated global remote tech jobs).
Zero API keys required.
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

_API_URL = "https://www.workingnomads.com/api/exposed_jobs/"
_TIMEOUT = 12.0
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


class WorkingNomadsSource(JobSourceBase):
    """
    Working Nomads remote job discovery source.
    Fetches real, curated remote positions from workingnomads.com.
    """

    @property
    def source_name(self) -> str:
        return "workingnomads"

    @property
    def is_configured(self) -> bool:
        return True

    async def search_jobs(self, criteria: SearchCriteria) -> List[NormalizedJob]:
        keywords_list = [k.lower().strip() for k in (criteria.get("keywords") or []) if k.strip()]
        location_str = (criteria.get("location") or "").lower().strip()

        headers = {
            "User-Agent": _USER_AGENT,
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
                resp = await client.get(_API_URL, headers=headers)
                if resp.status_code != 200:
                    logger.warning("Working Nomads HTTP %d", resp.status_code)
                    return []
                raw_jobs = resp.json()
        except Exception as exc:
            logger.warning("Working Nomads fetch error: %s", exc)
            return []

        if not isinstance(raw_jobs, list):
            return []

        results: List[NormalizedJob] = []

        for item in raw_jobs:
            title = (item.get("title") or "").strip()
            if not title:
                continue

            company = (item.get("company_name") or "Working Nomads Partner").strip()
            url = (item.get("url") or "").strip()
            desc = item.get("description") or ""
            tags_str = item.get("tags") or ""
            job_loc = item.get("location") or "Worldwide / Remote"
            pub_date_str = item.get("pub_date")

            combined_text = f"{title} {company} {desc} {tags_str}".lower()

            # Filter by keywords if provided
            if keywords_list:
                match = any(kw in combined_text for kw in keywords_list)
                if not match:
                    continue

            # Filter by location if specified
            if location_str and location_str not in ("remote", "any", "worldwide", "all"):
                if location_str not in job_loc.lower():
                    continue

            posted_at = None
            if pub_date_str:
                try:
                    posted_at = datetime.fromisoformat(pub_date_str)
                except Exception:
                    pass

            skills = [t.strip().lower() for t in tags_str.split(",") if t.strip()]
            for kw in keywords_list:
                if kw in combined_text and kw not in skills:
                    skills.append(kw)

            ext_id = f"wn_{abs(hash(url or (title + company)))}"

            job: NormalizedJob = {
                "external_id": ext_id,
                "source": "workingnomads",
                "title": title,
                "company_name": company,
                "description": desc or f"{title} at {company}",
                "canonical_url": url,
                "apply_url": url,
                "location": job_loc,
                "is_remote": True,
                "is_hybrid": False,
                "work_mode": "remote",
                "employment_type": criteria.get("employment_type") or "full-time",
                "experience_min_years": criteria.get("experience_min_years"),
                "experience_max_years": criteria.get("experience_max_years"),
                "required_skills": skills[:10],
                "posted_at": posted_at,
                "discovered_at": datetime.now(timezone.utc),
                "raw_data": {"id": ext_id, "source": "workingnomads", "url": url},
            }
            results.append(job)

        logger.info("Working Nomads source returned %d matching jobs", len(results))
        return results
