"""
backend/jobs/sources/hackernews.py

Hacker News "Who is Hiring?" job discovery source.
Queries Y Combinator's official monthly "Ask HN: Who is hiring?" mega-threads
via the public Algolia HN search API.
Provides direct access to tech startups, founder-led engineering teams, and high-paying tech roles.
Zero API keys required.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

from jobs.sources.base import (
    JobSourceBase,
    NormalizedJob,
    SearchCriteria,
)

logger = logging.getLogger(__name__)

_ALGOLIA_URL = "https://hn.algolia.com/api/v1"
_TIMEOUT = 12.0
_USER_AGENT = "AI-Job-Hunter-Bot/1.0"


class HackerNewsSource(JobSourceBase):
    """
    Hacker News "Who is hiring" monthly thread search source.
    """

    @property
    def source_name(self) -> str:
        return "hackernews"

    @property
    def is_configured(self) -> bool:
        return True

    async def search_jobs(self, criteria: SearchCriteria) -> List[NormalizedJob]:
        keywords_list = [k.strip() for k in (criteria.get("keywords") or []) if k.strip()]
        search_query = " ".join(keywords_list).strip() or "engineer"
        location_filter = (criteria.get("location") or "").lower().strip()

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT, headers={"User-Agent": _USER_AGENT}) as client:
                # 1. Fetch latest "Who is hiring" story ID
                story_resp = await client.get(
                    f"{_ALGOLIA_URL}/search_by_date",
                    params={"tags": "story,author_whoishiring", "query": "hiring", "hitsPerPage": 1},
                )
                if story_resp.status_code != 200:
                    return []
                story_hits = story_resp.json().get("hits", [])
                if not story_hits:
                    return []
                story_id = story_hits[0].get("objectID")
                if not story_id:
                    return []

                # 2. Query comments matching the keywords inside that story
                comments_resp = await client.get(
                    f"{_ALGOLIA_URL}/search",
                    params={
                        "tags": f"comment,story_{story_id}",
                        "query": search_query,
                        "hitsPerPage": 30,
                    },
                )
                if comments_resp.status_code != 200:
                    return []
                comment_hits = comments_resp.json().get("hits", [])
        except Exception as exc:
            logger.warning("Hacker News fetch error: %s", exc)
            return []

        results: List[NormalizedJob] = []

        for hit in comment_hits:
            raw_html = hit.get("comment_text") or ""
            if not raw_html:
                continue

            soup = BeautifulSoup(raw_html, "html.parser")
            text = soup.get_text("\n").strip()
            if not text:
                continue

            first_line = text.split("\n")[0].strip()
            # Standard HN format: Company | Role | Location | Employment | Salary
            parts = [p.strip() for p in first_line.split("|")]
            if len(parts) >= 2:
                company = parts[0]
                title = parts[1]
                loc_part = parts[2] if len(parts) > 2 else "Remote / Global"
            else:
                # If no pipes, skip or treat as discussion comment
                if len(first_line) > 100 or "seeking" in first_line.lower():
                    continue
                company = "YC / HN Startup"
                title = first_line[:80]
                loc_part = "Remote"

            # Skip candidate self-promotions
            if "seeking work" in text.lower() or "actively seeking" in text.lower():
                continue

            # Check location filter if requested
            if location_filter and location_filter not in ("remote", "any", "worldwide", "all"):
                if location_filter not in loc_part.lower() and location_filter not in text.lower():
                    continue

            # Find apply link inside HTML or fallback to HN item URL
            links = [
                a.get("href")
                for a in soup.find_all("a")
                if a.get("href") and "news.ycombinator.com" not in a.get("href")
            ]
            hn_url = f"https://news.ycombinator.com/item?id={hit['objectID']}"
            apply_url = links[0] if links else hn_url

            is_remote = bool(
                criteria.get("remote")
                or "remote" in loc_part.lower()
                or "remote" in text.lower()
            )

            created_at_str = hit.get("created_at")
            posted_at = None
            if created_at_str:
                try:
                    posted_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                except Exception:
                    pass

            ext_id = f"hn_{hit['objectID']}"

            job: NormalizedJob = {
                "external_id": ext_id,
                "source": "hackernews",
                "title": title,
                "company_name": company,
                "description": text[:1500],
                "canonical_url": hn_url,
                "apply_url": apply_url,
                "location": loc_part,
                "is_remote": is_remote,
                "is_hybrid": False,
                "work_mode": "remote" if is_remote else "onsite",
                "employment_type": criteria.get("employment_type") or "full-time",
                "experience_min_years": criteria.get("experience_min_years"),
                "experience_max_years": criteria.get("experience_max_years"),
                "required_skills": [k.lower() for k in keywords_list],
                "posted_at": posted_at,
                "discovered_at": datetime.now(timezone.utc),
                "raw_data": {"id": ext_id, "source": "hackernews", "url": apply_url},
            }
            results.append(job)

        logger.info("Hacker News source returned %d jobs for '%s'", len(results), search_query)
        return results
