"""
backend/jobs/sources/registry.py

Source registry — manages all known job discovery sources.

Usage:
    registry = JobSourceRegistry.from_settings()
    sources = registry.enabled_sources()
    source = registry.get("adzuna")

Sources are instantiated lazily and only once.
Adding a new source: register it in _build_all().
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from jobs.sources.base import JobSourceBase

logger = logging.getLogger(__name__)


class JobSourceRegistry:
    """Registry of all configured job discovery sources."""

    def __init__(self) -> None:
        self._sources: Dict[str, JobSourceBase] = {}

    def register(self, source: JobSourceBase) -> None:
        """Add a source to the registry."""
        self._sources[source.source_name] = source
        status = "configured" if source.is_configured else "NOT configured"
        logger.info("Job source registered: %s [%s]", source.source_name, status)

    def get(self, name: str) -> Optional[JobSourceBase]:
        """Return source by name, or None if not found."""
        return self._sources.get(name)

    def enabled_sources(self) -> List[JobSourceBase]:
        """Return all sources that are properly configured."""
        return [s for s in self._sources.values() if s.is_configured]

    def all_sources(self) -> List[JobSourceBase]:
        """Return all registered sources regardless of configuration."""
        return list(self._sources.values())

    def source_statuses(self) -> Dict[str, Dict[str, str]]:
        """
        Return a status dict for all registered sources.
        Used by the configuration/status API endpoint.
        """
        return {
            name: {
                "configured": str(source.is_configured),
                "status": "ready" if source.is_configured else "missing_credentials",
            }
            for name, source in self._sources.items()
        }

    @classmethod
    def from_settings(cls) -> "JobSourceRegistry":
        """
        Build and return a registry populated from application settings.
        Add new sources here as they are implemented.
        """
        from app.core.config import settings
        from jobs.sources.adzuna import AdzunaSource
        from jobs.sources.remotive import RemotiveSource
        from jobs.sources.arbeitnow import ArbeitnowSource
        from jobs.sources.himalayas import HimalayasSource
        from jobs.sources.jobicy import JobicySource
        from jobs.sources.themuse import TheMuseSource
        from jobs.sources.linkedin import LinkedInSource
        from jobs.sources.remoteok import RemoteOKSource
        from jobs.sources.weworkremotely import WeWorkRemotelySource
        from jobs.sources.workingnomads import WorkingNomadsSource
        from jobs.sources.jobspresso import JobspressoSource
        from jobs.sources.hackernews import HackerNewsSource

        registry = cls()

        # 1. LinkedIn — Public global job search across all companies & locations
        registry.register(LinkedInSource())

        # 2. RemoteOK — High-growth tech, software development & AI roles
        registry.register(RemoteOKSource())

        # 3. We Work Remotely (WWR) — Premier global remote programming jobs
        registry.register(WeWorkRemotelySource())

        # 4. Working Nomads — Curated global remote engineering roles
        registry.register(WorkingNomadsSource())

        # 5. Jobspresso — High quality remote careers with direct ATS application links
        registry.register(JobspressoSource())

        # 6. Hacker News — YC & startup founder hiring from official monthly threads
        registry.register(HackerNewsSource())

        # 7. Remotive — Global remote engineering & tech jobs
        registry.register(RemotiveSource())

        # 8. Arbeitnow — European, US & global software engineering jobs
        registry.register(ArbeitnowSource())

        # 9. Himalayas — Worldwide remote developer & modern tech jobs
        registry.register(HimalayasSource())

        # 10. Jobicy — Global tech & programming remote jobs
        registry.register(JobicySource())

        # 11. The Muse — Top global tech enterprise & startup careers
        registry.register(TheMuseSource())

        # 12. Adzuna — Country/Region specific job search API
        registry.register(AdzunaSource(
            app_id=settings.ADZUNA_APP_ID,
            app_key=settings.ADZUNA_APP_KEY,
            country=settings.ADZUNA_COUNTRY,
        ))

        return registry


# Module-level singleton (re-created on demand — no caching to allow test overrides)
def get_registry() -> JobSourceRegistry:
    """Return a fresh registry from current settings."""
    return JobSourceRegistry.from_settings()
