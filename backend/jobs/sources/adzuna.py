"""
backend/jobs/sources/adzuna.py

Adzuna Job Search API source.

Adzuna provides a free-tier REST API for job search.
Sign up at: https://developer.adzuna.com/

Required config:
  ADZUNA_APP_ID   — Your Adzuna App ID
  ADZUNA_APP_KEY  — Your Adzuna App Key
  ADZUNA_COUNTRY  — ISO country code (default: "in" for India)

If credentials are missing, is_configured returns False.
search_jobs() raises SourceNotConfiguredError rather than crashing.

API docs: https://api.adzuna.com/v1/api/
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs

import httpx

from jobs.sources.base import (
    JobSourceBase, NormalizedJob, SearchCriteria,
    SourceFetchError, SourceNotConfiguredError,
)

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.adzuna.com/v1/api/jobs"
_REQUEST_TIMEOUT = 15.0   # seconds
_MAX_RESULTS_PER_PAGE = 50

# Adzuna employment type normalization
_EMPLOYMENT_TYPE_MAP: Dict[str, str] = {
    "permanent": "full-time",
    "contract": "contract",
    "part time": "part-time",
    "part-time": "part-time",
    "temporary": "contract",
    "internship": "internship",
    "graduate": "graduate",
}


class AdzunaSource(JobSourceBase):
    """
    Fetches jobs from the Adzuna Job Search API.

    Pagination: Adzuna is 1-indexed (page=1 is first page).
    Rate limiting: Adzuna free tier allows reasonable usage.
                   We use a single request per search_jobs() call.
    """

    def __init__(
        self,
        app_id: Optional[str],
        app_key: Optional[str],
        country: str = "in",
    ) -> None:
        self._app_id = app_id or ""
        self._app_key = app_key or ""
        self._country = country or "in"

    @property
    def source_name(self) -> str:
        return "adzuna"

    @property
    def is_configured(self) -> bool:
        return bool(self._app_id.strip() and self._app_key.strip())

    async def search_jobs(self, criteria: SearchCriteria) -> List[NormalizedJob]:
        """
        Query the Adzuna API and return normalized job listings.

        Raises:
            SourceNotConfiguredError: if credentials are missing.
            SourceFetchError: on HTTP/network errors.
        """
        self.assert_configured()

        page = criteria.get("page", 1)
        page_size = min(criteria.get("page_size", 20), _MAX_RESULTS_PER_PAGE)
        country = criteria.get("country") or self._country

        params = self._build_params(criteria, page, page_size)
        url = f"{_BASE_URL}/{country}/search/{page}"

        logger.info(
            "Adzuna search: country=%s page=%d page_size=%d keywords=%s",
            country, page, page_size,
            criteria.get("keywords", []),
        )

        try:
            async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
                response = await client.get(url, params=params)

            if response.status_code == 401:
                raise SourceNotConfiguredError(
                    "Adzuna returned 401 Unauthorized. Check ADZUNA_APP_ID and ADZUNA_APP_KEY."
                )
            if response.status_code == 429:
                raise SourceFetchError(
                    "Adzuna rate limit exceeded (429). Wait before retrying."
                )
            if response.status_code >= 400:
                raise SourceFetchError(
                    f"Adzuna API returned HTTP {response.status_code}: {response.text[:200]}"
                )

            data = response.json()

        except httpx.TimeoutException as exc:
            raise SourceFetchError(f"Adzuna request timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise SourceFetchError(f"Adzuna network error: {exc}") from exc

        results: List[Dict[str, Any]] = data.get("results", [])
        logger.info("Adzuna returned %d results (page %d)", len(results), page)

        normalized: List[NormalizedJob] = []
        for raw in results:
            job = self._normalize(raw, country)
            if job:
                normalized.append(job)

        return normalized

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _build_params(
        self,
        criteria: SearchCriteria,
        page: int,
        page_size: int,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "app_id": self._app_id,
            "app_key": self._app_key,
            "results_per_page": page_size,
            "content-type": "application/json",
        }

        keywords: List[str] = criteria.get("keywords", [])
        if keywords:
            params["what"] = " ".join(keywords)

        location = criteria.get("location")
        if location:
            params["where"] = location

        if criteria.get("remote"):
            # Adzuna supports "where=remote" as a filter
            params["where"] = "remote"

        salary_min = criteria.get("salary_min")
        if salary_min:
            params["salary_min"] = salary_min

        salary_max = criteria.get("salary_max")
        if salary_max:
            params["salary_max"] = salary_max

        posted_within_days = criteria.get("posted_within_days")
        if posted_within_days:
            params["max_days_old"] = posted_within_days

        # Sort by date descending (most recent first)
        params["sort_by"] = "date"
        params["sort_direction"] = "down"

        return params

    def _normalize(
        self, raw: Dict[str, Any], country: str
    ) -> Optional[NormalizedJob]:
        """Convert a single Adzuna job dict to a NormalizedJob."""
        external_id = str(raw.get("id", "")).strip()
        title = (raw.get("title") or "").strip()
        company_name = (
            raw.get("company", {}).get("display_name") or "Unknown"
        ).strip()

        if not external_id or not title:
            logger.debug("Skipping Adzuna result with missing id or title: %s", raw)
            return None

        # URLs — strip Adzuna redirect tracking from canonical URL
        redirect_url: str = raw.get("redirect_url") or ""
        canonical_url = self._extract_canonical_url(redirect_url) or redirect_url

        # Location
        location_data = raw.get("location", {})
        location_parts = location_data.get("area", [])
        location = ", ".join(str(p) for p in location_parts if p) or None

        # Work mode
        description_raw: str = raw.get("description") or ""
        desc_lower = description_raw.lower()
        is_remote = "remote" in desc_lower or "work from home" in desc_lower or "wfh" in desc_lower
        is_hybrid = "hybrid" in desc_lower
        work_mode = (
            "remote" if is_remote
            else "hybrid" if is_hybrid
            else "onsite"
        )

        # Employment type
        contract_type: str = (raw.get("contract_type") or "").lower()
        contract_time: str = (raw.get("contract_time") or "").lower()
        employment_type = _EMPLOYMENT_TYPE_MAP.get(
            contract_type,
            _EMPLOYMENT_TYPE_MAP.get(contract_time, "full-time")
        )

        # Salary
        salary_min: Optional[int] = None
        salary_max: Optional[int] = None
        if raw.get("salary_min"):
            try:
                salary_min = int(float(raw["salary_min"]))
            except (ValueError, TypeError):
                pass
        if raw.get("salary_max"):
            try:
                salary_max = int(float(raw["salary_max"]))
            except (ValueError, TypeError):
                pass
        salary_currency = "GBP" if country == "gb" else "USD" if country == "us" else "INR"

        # Posted date
        posted_at: Optional[datetime] = None
        created_str: str = raw.get("created") or ""
        if created_str:
            try:
                posted_at = datetime.fromisoformat(
                    created_str.replace("Z", "+00:00")
                )
            except ValueError:
                pass

        return NormalizedJob(
            external_id=external_id,
            source=self.source_name,
            title=title,
            company_name=company_name,
            description=description_raw or None,
            requirements=None,  # Adzuna combines requirements into description
            canonical_url=canonical_url or None,
            apply_url=redirect_url or None,
            location=location,
            is_remote=is_remote,
            is_hybrid=is_hybrid,
            work_mode=work_mode,
            employment_type=employment_type,
            experience_min_years=None,  # Not provided by Adzuna
            experience_max_years=None,
            required_skills=None,       # Extracted by AI/normalizer from description
            preferred_skills=None,
            education_required=None,
            graduation_year_required=None,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary_currency,
            posted_at=posted_at,
            discovered_at=datetime.now(timezone.utc),
            raw_data={
                "adzuna_id": external_id,
                "country": country,
                "category": raw.get("category", {}).get("label"),
                "adref": raw.get("adref"),
            },
        )

    @staticmethod
    def _extract_canonical_url(url: str) -> Optional[str]:
        """
        Remove Adzuna tracking/redirect wrapper from a job URL.

        Adzuna URLs look like:
          https://www.adzuna.in/land/ad/1234?sc=...&v=1&...
        We return the URL as-is since extracting the final employer URL
        would require following the redirect (which we avoid).
        We do strip known tracking query parameters.
        """
        if not url:
            return None
        try:
            parsed = urlparse(url)
            # Remove known tracking params
            tracking_params = {"utm_source", "utm_medium", "utm_campaign",
                               "utm_term", "utm_content", "sc", "v", "cty",
                               "adref", "ref"}
            query = parse_qs(parsed.query, keep_blank_values=False)
            clean_query = {
                k: v for k, v in query.items()
                if k.lower() not in tracking_params
            }
            # Rebuild without tracking params
            from urllib.parse import urlencode
            new_query = urlencode(
                {k: v[0] for k, v in clean_query.items()}, doseq=False
            ) if clean_query else ""
            return urlunparse((
                parsed.scheme, parsed.netloc, parsed.path,
                parsed.params, new_query, ""
            ))
        except Exception:
            return url
