"""
backend/jobs/sources/weworkremotely.py

We Work Remotely (WWR) public jobs source.
Fetches top programming, devops, product, and full-stack remote jobs.
Free open RSS feed — zero keys needed.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

from jobs.sources.base import (
    JobSourceBase,
    NormalizedJob,
    SearchCriteria,
)

logger = logging.getLogger(__name__)

_RSS_FEEDS = [
    "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
]
_TIMEOUT = 12.0
_USER_AGENT = "JobApplyBot/1.0 (contact@jobapplybot.org; Automated Job Search Engine)"


class WeWorkRemotelySource(JobSourceBase):
    """
    We Work Remotely RSS feed source.
    """

    @property
    def source_name(self) -> str:
        return "weworkremotely"

    @property
    def is_configured(self) -> bool:
        return True

    async def search_jobs(self, criteria: SearchCriteria) -> List[NormalizedJob]:
        keywords = [k.lower().strip() for k in criteria.get("keywords") or [] if k.strip()]
        location_filter = (criteria.get("location") or "").lower()

        headers = {
            "User-Agent": _USER_AGENT,
            "Accept": "application/rss+xml, application/xml, text/xml",
        }

        async def _fetch_feed(url: str, client: httpx.AsyncClient) -> List[Any]:
            try:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "xml")
                    return soup.find_all("item")
            except Exception as e:
                logger.warning("WWR feed %s error: %s", url, e)
            return []

        items: List[Any] = []
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
                feed_tasks = [_fetch_feed(feed_url, client) for feed_url in _RSS_FEEDS]
                feed_results = await asyncio.gather(*feed_tasks)
                for res in feed_results:
                    items.extend(res)
        except Exception as exc:
            logger.warning("WWR fetch error: %s", exc)
            return []
        results: List[NormalizedJob] = []

        for item in items:
            raw_title = item.find("title").text.strip() if item.find("title") else ""
            if not raw_title:
                continue

            # WWR titles are usually formatted: "CompanyName: Job Title"
            company = "Unknown"
            title = raw_title
            if ":" in raw_title:
                parts = raw_title.split(":", 1)
                company = parts[0].strip()
                title = parts[1].strip()

            link = item.find("link").text.strip() if item.find("link") else ""
            desc = item.find("description").text.strip() if item.find("description") else ""

            # Filter keywords if provided
            if keywords:
                full_text = f"{title} {company} {desc[:800]}".lower()
                if not any(kw in full_text for kw in keywords):
                    continue

            posted_at = None
            pub_date = item.find("pubDate")
            if pub_date and pub_date.text:
                try:
                    posted_at = parsedate_to_datetime(pub_date.text.strip())
                except Exception:
                    pass

            # Extract job ID from link e.g. /remote-jobs/{slug}
            ext_id = f"wwr_{abs(hash(link or (title + company)))}"

            job: NormalizedJob = {
                "external_id": ext_id,
                "source": "weworkremotely",
                "title": title,
                "company_name": company,
                "description": desc,
                "canonical_url": link,
                "apply_url": link,
                "location": "Worldwide / Remote",
                "is_remote": True,
                "is_hybrid": False,
                "work_mode": "remote",
                "employment_type": "full-time",
                "experience_min_years": criteria.get("experience_min_years"),
                "experience_max_years": criteria.get("experience_max_years"),
                "required_skills": [k for k in keywords if k],
                "posted_at": posted_at,
                "discovered_at": datetime.now(timezone.utc),
                "raw_data": {"id": ext_id, "source": "weworkremotely", "url": link},
            }
            results.append(job)
            if len(results) >= criteria.get("page_size", 25):
                break

        logger.info("We Work Remotely source returned %d matching jobs", len(results))
        return results
