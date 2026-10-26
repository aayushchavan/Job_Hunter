"""
backend/jobs/sources/base.py

Abstract base class for all job discovery sources.

Every source implementation must:
  1. Inherit from JobSource.
  2. Implement search_jobs() returning a list of NormalizedJob dicts.
  3. Never fabricate jobs — all data must come from the external source.
  4. Raise SourceNotConfiguredError if required credentials are missing.
  5. Raise SourceFetchError on network/API failures (do not swallow them).

The NormalizedJob TypedDict defines the canonical structure every source
must return. Use None for fields the source does not provide.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from typing_extensions import TypedDict


class NormalizedJob(TypedDict, total=False):
    """
    Canonical job structure returned by every source.
    All fields are optional except external_id, source, title, company_name.
    """
    # Identity
    external_id: str                    # Source's own job ID
    source: str                         # Source name, e.g. "adzuna"
    fingerprint: Optional[str]          # SHA-256 for deduplication fallback

    # Core content
    title: str
    company_name: str
    description: Optional[str]
    requirements: Optional[str]

    # URLs
    canonical_url: Optional[str]        # Canonical/tracking-free job URL
    apply_url: Optional[str]            # Direct application URL

    # Location
    location: Optional[str]
    is_remote: Optional[bool]
    is_hybrid: Optional[bool]
    work_mode: Optional[str]            # "remote" | "hybrid" | "onsite" | "unknown"

    # Employment
    employment_type: Optional[str]      # "full-time" | "part-time" | "contract" | ...
    experience_min_years: Optional[int]
    experience_max_years: Optional[int]

    # Skills
    required_skills: Optional[List[str]]
    preferred_skills: Optional[List[str]]

    # Education
    education_required: Optional[str]
    graduation_year_required: Optional[int]

    # Salary
    salary_min: Optional[int]
    salary_max: Optional[int]
    salary_currency: Optional[str]

    # Dates
    posted_at: Optional[datetime]
    discovered_at: Optional[datetime]

    # Raw data (stored for debugging/future use)
    raw_data: Optional[Dict[str, Any]]


class SearchCriteria(TypedDict, total=False):
    """Parameters passed to source.search_jobs()."""
    keywords: List[str]
    location: Optional[str]
    country: Optional[str]          # ISO country code e.g. "in", "gb", "us"
    remote: Optional[bool]
    employment_type: Optional[str]
    salary_min: Optional[int]
    salary_max: Optional[int]
    experience_years: Optional[int]
    experience_min_years: Optional[int]
    experience_max_years: Optional[int]
    posted_within_days: Optional[int]
    page: int
    page_size: int


class SourceNotConfiguredError(Exception):
    """Raised when a source lacks required credentials or configuration."""


class SourceFetchError(Exception):
    """Raised when a source API call fails (network, HTTP error, etc.)."""


class JobSourceBase(ABC):
    """
    Abstract base for all job discovery sources.
    Subclasses must implement: source_name, is_configured, search_jobs.
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Machine-readable source identifier, e.g. 'adzuna'."""

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """True if all required credentials/config are present."""

    @abstractmethod
    async def search_jobs(self, criteria: SearchCriteria) -> List[NormalizedJob]:
        """
        Fetch and return normalized jobs matching the given criteria.

        Raises:
            SourceNotConfiguredError: if credentials are missing.
            SourceFetchError: on network or API failures.
        """

    def assert_configured(self) -> None:
        """Call this at the start of search_jobs() if not configured."""
        if not self.is_configured:
            raise SourceNotConfiguredError(
                f"Source '{self.source_name}' is not configured. "
                f"Check the required environment variables."
            )
