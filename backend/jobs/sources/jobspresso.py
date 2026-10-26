"""
backend/jobs/sources/jobspresso.py

Jobspresso job discovery source using WordPress REST API.
Curated remote careers in tech, software engineering, product, and AI.
Includes direct company ATS application links (Ashby, Greenhouse, Lever, etc.).
Zero API keys required.
"""
from __future__ import annotations

import html
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from jobs.sources.base import (
    JobSourceBase,
    NormalizedJob,
    SearchCriteria,
)

logger = logging.getLogger(__name__)

_API_URL = "https://jobspresso.co/wp-json/wp/v2/job-listings"
_TIMEOUT = 12.0
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


class JobspressoSource(JobSourceBase):
    """
    Jobspresso curated remote job discovery source.
    """

    @property
    def source_name(self) -> str:
        return "jobspresso"

    @property
    def is_configured(self) -> bool:
        return True

    async def search_jobs(self, criteria: SearchCriteria) -> List[NormalizedJob]:
        keywords_list = [k.strip() for k in (criteria.get("keywords") or []) if k.strip()]
        search_query = " ".join(keywords_list).strip() or "developer"
        location_str = (criteria.get("location") or "").lower().strip()

        params: Dict[str, Any] = {
            "per_page": 30,
            "search": search_query,
        }

        headers = {
            "User-Agent": _USER_AGENT,
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
                resp = await client.get(_API_URL, params=params, headers=headers)
                if resp.status_code != 200:
                    logger.warning("Jobspresso HTTP %d", resp.status_code)
                    return []
                raw_jobs = resp.json()
        except Exception as exc:
            logger.warning("Jobspresso fetch error: %s", exc)
            return []

        if not isinstance(raw_jobs, list):
            return []

        results: List[NormalizedJob] = []

        for item in raw_jobs:
            raw_title = item.get("title", {}).get("rendered") or ""
            title = html.unescape(raw_title).strip()
            if not title:
                continue

            meta = item.get("meta") or {}
            company = meta.get("_company_name") or "Tech Company"
            job_loc = meta.get("_job_location") or "Worldwide / Remote"
            apply_url = meta.get("_application") or item.get("link") or ""
            canonical_url = item.get("link") or apply_url

            # Filter location if specified
            if location_str and location_str not in ("remote", "any", "worldwide", "all"):
                if location_str not in job_loc.lower():
                    continue

            raw_content = item.get("content", {}).get("rendered") or ""
            # Strip tags for clean summary
            clean_desc = re.sub(r"<[^>]+>", " ", raw_content).strip()
            clean_desc = re.sub(r"\s+", " ", clean_desc)[:1500]

            date_str = item.get("date_gmt") or item.get("date")
            posted_at = None
            if date_str:
                try:
                    posted_at = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
                except Exception:
                    pass

            item_id = str(item.get("id") or abs(hash(canonical_url)))
            ext_id = f"jp_{item_id}"

            job: NormalizedJob = {
                "external_id": ext_id,
                "source": "jobspresso",
                "title": title,
                "company_name": company,
                "description": clean_desc or f"{title} at {company}",
                "canonical_url": canonical_url,
                "apply_url": apply_url,
                "location": job_loc,
                "is_remote": True,
                "is_hybrid": False,
                "work_mode": "remote",
                "employment_type": criteria.get("employment_type") or "full-time",
                "experience_min_years": criteria.get("experience_min_years"),
                "experience_max_years": criteria.get("experience_max_years"),
                "required_skills": [k.lower() for k in keywords_list],
                "posted_at": posted_at,
                "discovered_at": datetime.now(timezone.utc),
                "raw_data": {"id": ext_id, "source": "jobspresso", "url": apply_url},
            }
            results.append(job)

        logger.info("Jobspresso source returned %d jobs for '%s'", len(results), search_query)
        return results
