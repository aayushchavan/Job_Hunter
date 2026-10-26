"""
backend/jobs/sources/linkedin.py

LinkedIn Jobs discovery source using public guest job search API.
Fetches live jobs directly from LinkedIn for any keyword, role, and location worldwide.
Zero API keys required.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from jobs.sources.base import (
    JobSourceBase,
    NormalizedJob,
    SearchCriteria,
    SourceFetchError,
)

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
_TIMEOUT = 14.0
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


class LinkedInSource(JobSourceBase):
    """
    Public LinkedIn Jobs source.
    Scrapes live search cards from LinkedIn's guest job search API.
    """

    @property
    def source_name(self) -> str:
        return "linkedin"

    @property
    def is_configured(self) -> bool:
        return True

    async def search_jobs(self, criteria: SearchCriteria) -> List[NormalizedJob]:
        keywords_list = criteria.get("keywords") or []
        query_str = " ".join(keywords_list).strip() or "software engineer"
        location_str = criteria.get("location") or "Remote"
        page = max(1, criteria.get("page", 1))
        start = (page - 1) * 25

        params: Dict[str, Any] = {
            "keywords": query_str,
            "location": location_str,
            "start": start,
        }

        # LinkedIn remote filter: f_WT=2 means remote
        if criteria.get("remote") or "remote" in location_str.lower():
            params["f_WT"] = "2"

        # Experience filters: 1=intern, 2=entry, 3=associate, 4=mid-senior, 5=director, 6=exec
        exp_min = criteria.get("experience_min_years")
        exp_max = criteria.get("experience_max_years")
        if exp_max is not None and exp_max <= 2:
            params["f_E"] = "1,2,3"
        elif exp_min is not None and exp_min >= 5:
            params["f_E"] = "4,5"
        elif exp_min is not None and exp_min >= 2:
            params["f_E"] = "3,4"

        headers = {
            "User-Agent": _USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
                resp = await client.get(_SEARCH_URL, params=params, headers=headers)
                if resp.status_code == 429:
                    logger.warning("LinkedIn rate limited (429)")
                    return []
                resp.raise_for_status()
                html = resp.text
        except httpx.TimeoutException as exc:
            logger.warning("LinkedIn request timed out: %s", exc)
            return []
        except Exception as exc:
            logger.warning("LinkedIn fetch error: %s", exc)
            return []

        soup = BeautifulSoup(html, "html.parser")
        cards = soup.find_all("li")
        results: List[NormalizedJob] = []

        for card in cards:
            title_el = card.find("h3", class_=re.compile(r"base-search-card__title"))
            company_el = card.find("h4", class_=re.compile(r"base-search-card__subtitle"))
            link_el = card.find("a", class_=re.compile(r"base-card__full-link"))
            loc_el = card.find("span", class_=re.compile(r"job-search-card__location"))
            time_el = card.find("time")

            title = title_el.text.strip() if title_el else ""
            if not title:
                continue

            company = company_el.text.strip() if company_el else "Unknown Company"
            loc = loc_el.text.strip() if loc_el else location_str
            apply_url = link_el.get("href") if link_el else ""
            if apply_url and "?" in apply_url:
                # Strip query tracking params cleanly
                apply_url = apply_url.split("?")[0]

            # Extract job ID from urn or link
            job_urn = card.get("data-entity-urn") or ""
            job_id_match = re.search(r"jobPosting:(\d+)", job_urn)
            if job_id_match:
                ext_id = f"li_{job_id_match.group(1)}"
            elif apply_url:
                num_match = re.search(r"-(\d+)$", apply_url)
                ext_id = f"li_{num_match.group(1)}" if num_match else f"li_{abs(hash(apply_url))}"
            else:
                ext_id = f"li_{abs(hash(title + company))}"

            posted_at = None
            if time_el and time_el.get("datetime"):
                try:
                    posted_at = datetime.fromisoformat(time_el["datetime"])
                except Exception:
                    pass

            is_remote = bool(
                criteria.get("remote")
                or "remote" in loc.lower()
                or "remote" in title.lower()
            )

            job: NormalizedJob = {
                "external_id": ext_id,
                "source": "linkedin",
                "title": title,
                "company_name": company,
                "description": f"LinkedIn job posting for {title} at {company} ({loc}). Visit company apply link for full requirements and submission.",
                "canonical_url": apply_url,
                "apply_url": apply_url,
                "location": loc,
                "is_remote": is_remote,
                "is_hybrid": False,
                "work_mode": "remote" if is_remote else "onsite",
                "employment_type": criteria.get("employment_type") or "full-time",
                "experience_min_years": exp_min,
                "experience_max_years": exp_max,
                "required_skills": [k.lower() for k in keywords_list if k],
                "posted_at": posted_at,
                "discovered_at": datetime.now(timezone.utc),
                "raw_data": {"id": ext_id, "source": "linkedin", "url": apply_url},
            }
            results.append(job)

        logger.info("LinkedIn source returned %d jobs for '%s'", len(results), query_str)
        return results
