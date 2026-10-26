"""
backend/app/services/eligibility_service.py

Eligibility checker for Phase 1.
Checks ALL hard criteria BEFORE Claude match scoring.
If ANY hard criterion fails → REJECTED with reasons stored.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from app.models.eligibility import EligibilityCriteria
from app.models.job import Job
from app.models.user import User


@dataclass
class EligibilityResult:
    eligible: bool
    reasons: List[str] = field(default_factory=list)

    def reject(self, reason: str) -> None:
        self.eligible = False
        self.reasons.append(reason)


class EligibilityService:
    """
    Stateless hard-eligibility checker.
    Call check(user, job, criteria) to get an EligibilityResult.
    """

    def check(
        self,
        user: User,
        job: Job,
        criteria: Optional[EligibilityCriteria],
    ) -> EligibilityResult:
        """
        Run all hard checks. Returns EligibilityResult with eligible=True
        if ALL checks pass, otherwise eligible=False with all failure reasons.
        """
        result = EligibilityResult(eligible=True)

        if criteria is None or not criteria.is_active:
            # No criteria set — allow the job through
            return result

        self._check_experience(user, job, criteria, result)
        self._check_role(job, criteria, result)
        self._check_domain(job, criteria, result)
        self._check_location(job, criteria, result)
        self._check_salary(job, criteria, result)
        self._check_employment_type(job, criteria, result)
        self._check_company(job, criteria, result)
        self._check_education(job, criteria, result)

        return result

    # ── Individual checkers ───────────────────────────────────────────────────

    def _check_experience(
        self,
        user: User,
        job: Job,
        criteria: EligibilityCriteria,
        result: EligibilityResult,
    ) -> None:
        user_yoe = user.years_of_experience
        max_allowed = criteria.max_experience_years

        if max_allowed is not None and user_yoe is not None:
            if job.experience_min_years and job.experience_min_years > max_allowed:
                result.reject(
                    f"Experience requirement is {job.experience_min_years}+ years; "
                    f"user maximum is {max_allowed} years"
                )

    def _check_role(
        self,
        job: Job,
        criteria: EligibilityCriteria,
        result: EligibilityResult,
    ) -> None:
        title_lower = job.title.lower()

        # Excluded roles (hard stop)
        if criteria.excluded_roles:
            for excluded in criteria.excluded_roles:
                if excluded.lower() in title_lower:
                    result.reject(f"Role '{job.title}' contains excluded term '{excluded}'")
                    return

        # Allowed roles (must match at least one if specified)
        if criteria.allowed_roles:
            if not any(r.lower() in title_lower for r in criteria.allowed_roles):
                result.reject(
                    f"Role '{job.title}' does not match any allowed role: {criteria.allowed_roles}"
                )

    def _check_domain(
        self,
        job: Job,
        criteria: EligibilityCriteria,
        result: EligibilityResult,
    ) -> None:
        domain = (job.domain or "").lower()
        description = (job.description or "").lower()

        # Excluded domains — check both domain field and description text
        if criteria.excluded_domains:
            for excl in criteria.excluded_domains:
                if excl.lower() in domain or excl.lower() in description:
                    result.reject(f"Domain '{excl}' is in the excluded list")
                    return

        # Allowed domains — if specified, at least one must match
        if criteria.allowed_domains:
            if domain and not any(d.lower() in domain for d in criteria.allowed_domains):
                result.reject(
                    f"Domain '{job.domain}' is not in the allowed list: {criteria.allowed_domains}"
                )

    def _check_location(
        self,
        job: Job,
        criteria: EligibilityCriteria,
        result: EligibilityResult,
    ) -> None:
        if not criteria.allowed_locations:
            return

        job_location = (job.location or "").lower()
        is_remote = job.is_remote

        # Remote is allowed
        if is_remote and criteria.allow_remote:
            return

        # Check location match
        if not any(loc.lower() in job_location for loc in criteria.allowed_locations):
            result.reject(
                f"Location '{job.location}' is not in allowed locations: {criteria.allowed_locations}"
            )

    def _check_salary(
        self,
        job: Job,
        criteria: EligibilityCriteria,
        result: EligibilityResult,
    ) -> None:
        if criteria.min_salary is None:
            return
        if job.salary_max is not None and job.salary_max < criteria.min_salary:
            result.reject(
                f"Job maximum salary ({job.salary_max} {job.salary_currency}) "
                f"is below minimum ({criteria.min_salary} {criteria.salary_currency})"
            )

    def _check_employment_type(
        self,
        job: Job,
        criteria: EligibilityCriteria,
        result: EligibilityResult,
    ) -> None:
        if not criteria.allowed_employment_types:
            return
        if job.employment_type and job.employment_type.lower() not in [
            t.lower() for t in criteria.allowed_employment_types
        ]:
            result.reject(
                f"Employment type '{job.employment_type}' is not allowed: "
                f"{criteria.allowed_employment_types}"
            )

    def _check_company(
        self,
        job: Job,
        criteria: EligibilityCriteria,
        result: EligibilityResult,
    ) -> None:
        if not criteria.excluded_companies:
            return
        company_lower = job.company_name.lower()
        for excl in criteria.excluded_companies:
            if excl.lower() in company_lower:
                result.reject(f"Company '{job.company_name}' is in the excluded list")
                return

    def _check_education(
        self,
        job: Job,
        criteria: EligibilityCriteria,
        result: EligibilityResult,
    ) -> None:
        if criteria.graduation_year is not None and job.graduation_year_required is not None:
            if job.graduation_year_required > criteria.graduation_year:
                result.reject(
                    f"Job requires graduation year {job.graduation_year_required}; "
                    f"user graduated in {criteria.graduation_year}"
                )


# ── Singleton ──────────────────────────────────────────────────────────────────
eligibility_service = EligibilityService()
