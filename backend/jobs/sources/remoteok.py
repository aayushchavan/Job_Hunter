"""
backend/jobs/sources/remoteok.py

RemoteOK public API source.
Fetches high-quality remote software engineering, AI, DevOps, and tech jobs worldwide.
Free open API — zero keys needed.
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
)

logger = logging.getLogger(__name__)

_API_URL = "https://remoteok.com/api"
_TIMEOUT = 12.0
_USER_AGENT = "JobApplyBot/1.0 (contact@jobapplybot.org; Automated Job Search Engine)"


class RemoteOKSource(JobSourceBase):
    """
    RemoteOK open job board source.
    """

    @property
    def source_name(self) -> str:
        return "remoteok"

    @property
    def is_configured(self) -> bool:
        return True

    async def search_jobs(self, criteria: SearchCriteria) -> List[NormalizedJob]:
        keywords = [k.lower().strip() for k in criteria.get("keywords") or [] if k.strip()]
        location_filter = (criteria.get("location") or "").lower()

        headers = {
            "User-Agent": _USER_AGENT,
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
                resp = await client.get(_API_URL, headers=headers)
                if resp.status_code != 200:
                    logger.warning("RemoteOK returned status %d", resp.status_code)
                    return []
                raw_items = resp.json()
        except Exception as exc:
            logger.warning("RemoteOK fetch error: %s", exc)
            return []

        # First item in RemoteOK is usually legal/metadata dict
        if raw_items and isinstance(raw_items[0], dict) and not raw_items[0].get("position"):
            raw_items = raw_items[1:]

        results: List[NormalizedJob] = []

        for item in raw_items:
            if not isinstance(item, dict):
                continue
            position = item.get("position") or ""
            company = item.get("company") or "Unknown"
            if not position:
                continue

            desc = item.get("description") or ""
            apply_url = item.get("url") or item.get("apply_url") or ""
            if not apply_url and item.get("id"):
                apply_url = f"https://remoteok.com/remote-jobs/{item.get('id')}"

            tags = [t.lower() for t in item.get("tags") or []]
            location = item.get("location") or "Worldwide / Remote"

            # Filter by keywords if provided
            if keywords:
                full_text = f"{position} {company} {' '.join(tags)} {desc[:1000]}".lower()
                if not any(kw in full_text for kw in keywords):
                    continue

            # Filter by location if specified and not just "remote"
            if location_filter and location_filter != "remote" and location_filter not in location.lower() and "worldwide" not in location.lower():
                continue

            # Salary extraction
            sal_min = item.get("salary_min")
            sal_max = item.get("salary_max")
            try:
                sal_min = int(sal_min) if sal_min else None
                sal_max = int(sal_max) if sal_max else None
            except Exception:
                sal_min, sal_max = None, None

            posted_at = None
            date_str = item.get("date")
            if date_str:
                try:
                    posted_at = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                except Exception:
                    pass

            ext_id = f"rok_{item.get('id') or abs(hash(position + company))}"

            job: NormalizedJob = {
                "external_id": ext_id,
                "source": "remoteok",
                "title": position,
                "company_name": company,
                "description": desc,
                "canonical_url": apply_url,
                "apply_url": apply_url,
                "location": location,
                "is_remote": True,
                "is_hybrid": False,
                "work_mode": "remote",
                "employment_type": "full-time",
                "salary_min": sal_min,
                "salary_max": sal_max,
                "salary_currency": "USD" if (sal_min or sal_max) else None,
                "experience_min_years": criteria.get("experience_min_years"),
                "experience_max_years": criteria.get("experience_max_years"),
                "required_skills": tags[:8],
                "posted_at": posted_at,
                "discovered_at": datetime.now(timezone.utc),
                "raw_data": {"id": ext_id, "source": "remoteok"},
            }
            results.append(job)
            if len(results) >= criteria.get("page_size", 25):
                break

        logger.info("RemoteOK source returned %d matching jobs", len(results))
        return results
