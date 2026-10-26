"""
backend/app/ai/local_provider.py

LocalAIProvider — deterministic Python implementation of AIProvider.

Rules enforced here:
  - NO anthropic import anywhere in this file.
  - NO external API calls.
  - All results are reproducible given the same inputs.
  - NEVER invents experience, skills, or personal information.

Used when AI_PROVIDER=local (the default).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.ai.base import AIProvider, AnswerResult, MatchResult

# ── Skill synonym groups ───────────────────────────────────────────────────────
# Terms within the same group are treated as equivalent for matching.
_SKILL_SYNONYMS: List[Set[str]] = [
    {"python", "python3", "python 3"},
    {"javascript", "js", "node.js", "nodejs", "node js"},
    {"typescript", "ts"},
    {"react", "react.js", "reactjs"},
    {"fastapi", "fast api"},
    {"postgresql", "postgres", "psql"},
    {"rest api", "restful api", "rest apis", "restful apis", "rest"},
    {"docker", "dockerfile"},
    {"kubernetes", "k8s"},
    {"machine learning", "ml"},
    {"artificial intelligence", "ai"},
    {"natural language processing", "nlp"},
    {"sql", "mysql", "mssql"},
    {"aws", "amazon web services"},
    {"gcp", "google cloud", "google cloud platform"},
    {"azure", "microsoft azure"},
    {"git", "github", "gitlab"},
    {"ci/cd", "cicd", "continuous integration", "continuous deployment"},
    {"html", "html5"},
    {"css", "css3"},
    {"java", "java 8", "java 11", "java 17"},
    {"c#", "csharp", "c sharp"},
    {"c++", "cpp"},
    {"mongodb", "mongo"},
    {"redis", "redis cache"},
    {"elasticsearch", "elastic search"},
    {"django", "django rest framework", "drf"},
    {"flask"},
    {"spring", "spring boot", "spring framework"},
    {"microservices", "micro services", "microservice architecture"},
    {"agile", "scrum", "kanban"},
    {"linux", "ubuntu", "centos", "debian"},
]

# Build canonical → synonyms lookup
_CANONICAL: Dict[str, str] = {}  # any term → canonical (first in group)
for _group in _SKILL_SYNONYMS:
    _canon = sorted(_group)[0]
    for _term in _group:
        _CANONICAL[_term] = _canon


def _canonicalize(skill: str) -> str:
    """Return canonical form of a skill name."""
    return _CANONICAL.get(skill.lower().strip(), skill.lower().strip())


def _tokenize_skills(text: str) -> Set[str]:
    """Extract canonical skill tokens from free text."""
    if not text:
        return set()
    text_lower = text.lower()
    found: Set[str] = set()
    # Try multi-word synonyms first (longest match)
    all_terms = sorted(
        [t for group in _SKILL_SYNONYMS for t in group],
        key=len, reverse=True
    )
    for term in all_terms:
        if re.search(r"\b" + re.escape(term) + r"\b", text_lower):
            found.add(_canonicalize(term))
    return found


# ── Match score weights (must sum to 100) ─────────────────────────────────────
_WEIGHTS = {
    "role":            20,
    "experience":      20,
    "required_skills": 25,
    "preferred_skills":10,
    "location":        10,
    "salary":           5,
    "education":        5,
    "work_mode":        5,
}
assert sum(_WEIGHTS.values()) == 100


class LocalAIProvider(AIProvider):
    """
    Fully deterministic AI provider.
    No external calls. No anthropic import.
    """

    @property
    def provider_name(self) -> str:
        return "local"

    # ── Match scoring ──────────────────────────────────────────────────────────

    def score_job_match(
        self,
        job: Dict[str, Any],
        user_profile: Dict[str, Any],
    ) -> MatchResult:
        """
        Score 0–100 based on weighted keyword/skill matching.
        Each dimension contributes a fraction of its weight.
        """
        breakdown: Dict[str, int] = {}
        reasons: List[str] = []
        matched_skills: List[str] = []
        missing_skills: List[str] = []

        # ── Role match (20 pts) ────────────────────────────────────────────────
        role_score = self._score_role(job, user_profile, reasons)
        breakdown["role"] = role_score

        # ── Experience match (20 pts) ──────────────────────────────────────────
        exp_score = self._score_experience(job, user_profile, reasons)
        breakdown["experience"] = exp_score

        # ── Required skills (25 pts) ───────────────────────────────────────────
        req_score, matched, missing = self._score_required_skills(
            job, user_profile, reasons
        )
        breakdown["required_skills"] = req_score
        matched_skills.extend(matched)
        missing_skills.extend(missing)

        # ── Preferred skills (10 pts) ──────────────────────────────────────────
        pref_score = self._score_preferred_skills(job, user_profile, reasons)
        breakdown["preferred_skills"] = pref_score

        # ── Location (10 pts) ──────────────────────────────────────────────────
        loc_score = self._score_location(job, user_profile, reasons)
        breakdown["location"] = loc_score

        # ── Salary (5 pts) ─────────────────────────────────────────────────────
        sal_score = self._score_salary(job, user_profile, reasons)
        breakdown["salary"] = sal_score

        # ── Education (5 pts) ──────────────────────────────────────────────────
        edu_score = self._score_education(job, user_profile, reasons)
        breakdown["education"] = edu_score

        # ── Work mode (5 pts) ──────────────────────────────────────────────────
        wm_score = self._score_work_mode(job, user_profile, reasons)
        breakdown["work_mode"] = wm_score

        total = sum(breakdown.values())
        return MatchResult(
            score=min(100, max(0, total)),
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            reasons=reasons,
            breakdown=breakdown,
        )

    # ── Role scoring ───────────────────────────────────────────────────────────

    def _score_role(
        self,
        job: Dict[str, Any],
        user_profile: Dict[str, Any],
        reasons: List[str],
    ) -> int:
        weight = _WEIGHTS["role"]
        job_title = (job.get("title") or "").lower()
        user_title = (user_profile.get("current_title") or "").lower()
        allowed_roles: List[str] = [
            r.lower() for r in (user_profile.get("allowed_roles") or [])
        ]

        if not job_title:
            return weight  # no title info → full credit

        # Check against allowed roles
        if allowed_roles:
            if any(r in job_title or job_title in r for r in allowed_roles):
                reasons.append(f"Role '{job_title}' matches your target roles")
                return weight
            # Partial match
            for r in allowed_roles:
                words = set(r.split()) & set(job_title.split())
                if words:
                    partial = round(weight * 0.6)
                    reasons.append(f"Role '{job_title}' partially matches '{r}'")
                    return partial
            reasons.append(f"Role '{job_title}' does not match your target roles")
            return 0

        # Fallback: compare against current title
        if user_title and (user_title in job_title or job_title in user_title):
            return weight
        if user_title:
            words = set(user_title.split()) & set(job_title.split())
            if words:
                return round(weight * 0.7)
        return round(weight * 0.5)

    # ── Experience scoring ─────────────────────────────────────────────────────

    def _score_experience(
        self,
        job: Dict[str, Any],
        user_profile: Dict[str, Any],
        reasons: List[str],
    ) -> int:
        weight = _WEIGHTS["experience"]
        user_yoe: Optional[int] = user_profile.get("years_of_experience")
        job_min: Optional[int] = job.get("experience_min_years")
        job_max: Optional[int] = job.get("experience_max_years")

        if user_yoe is None or job_min is None:
            return weight  # not enough info → full credit

        if user_yoe < job_min:
            deficit = job_min - user_yoe
            if deficit <= 1:
                reasons.append(f"Experience: {user_yoe} yrs (need {job_min}) — close match")
                return round(weight * 0.5)
            reasons.append(f"Experience: {user_yoe} yrs below requirement of {job_min} yrs")
            return 0

        if job_max is not None and user_yoe > job_max + 3:
            reasons.append(f"Experience: {user_yoe} yrs above range ({job_min}–{job_max})")
            return round(weight * 0.7)

        reasons.append(f"Experience: {user_yoe} yrs within range ({job_min}–{job_max or '∞'})")
        return weight

    # ── Required skills scoring ────────────────────────────────────────────────

    def _score_required_skills(
        self,
        job: Dict[str, Any],
        user_profile: Dict[str, Any],
        reasons: List[str],
    ) -> Tuple[int, List[str], List[str]]:
        weight = _WEIGHTS["required_skills"]
        job_skills_raw: List[str] = job.get("required_skills") or []
        user_skills_raw: List[str] = user_profile.get("skills") or []

        # Also extract from description if skills list is empty
        if not job_skills_raw:
            desc = (job.get("description") or "") + " " + (job.get("requirements") or "")
            job_skills_raw = list(_tokenize_skills(desc))

        if not job_skills_raw:
            return weight, [], []  # no skills listed → full credit

        job_canon = {_canonicalize(s) for s in job_skills_raw}
        user_canon = {_canonicalize(s) for s in user_skills_raw}

        # Also extract skills from resume/summary text
        summary_text = (user_profile.get("summary") or "") + " " + (user_profile.get("resume_text") or "")
        user_canon |= _tokenize_skills(summary_text)

        matched = sorted(job_canon & user_canon)
        missing = sorted(job_canon - user_canon)

        if not job_canon:
            return weight, [], []

        ratio = len(matched) / len(job_canon)
        score = round(weight * ratio)

        if matched:
            reasons.append(f"Skills matched: {', '.join(matched[:5])}" + (" ..." if len(matched) > 5 else ""))
        if missing:
            reasons.append(f"Skills missing: {', '.join(missing[:5])}" + (" ..." if len(missing) > 5 else ""))

        return score, matched, missing

    # ── Preferred skills scoring ───────────────────────────────────────────────

    def _score_preferred_skills(
        self,
        job: Dict[str, Any],
        user_profile: Dict[str, Any],
        reasons: List[str],
    ) -> int:
        weight = _WEIGHTS["preferred_skills"]
        pref_raw: List[str] = job.get("preferred_skills") or []
        if not pref_raw:
            return weight  # no preferred skills listed → full credit

        user_skills_raw: List[str] = user_profile.get("skills") or []
        summary_text = (user_profile.get("summary") or "") + " " + (user_profile.get("resume_text") or "")
        user_canon = {_canonicalize(s) for s in user_skills_raw} | _tokenize_skills(summary_text)
        pref_canon = {_canonicalize(s) for s in pref_raw}

        matched = pref_canon & user_canon
        if not pref_canon:
            return weight
        ratio = len(matched) / len(pref_canon)
        return round(weight * ratio)

    # ── Location scoring ───────────────────────────────────────────────────────

    def _score_location(
        self,
        job: Dict[str, Any],
        user_profile: Dict[str, Any],
        reasons: List[str],
    ) -> int:
        weight = _WEIGHTS["location"]
        is_remote: Optional[bool] = job.get("is_remote")
        job_location = (job.get("location") or "").lower()
        user_city = (user_profile.get("city") or "").lower()
        user_locations: List[str] = [
            loc.lower() for loc in (user_profile.get("preferred_locations") or [])
        ]

        if is_remote:
            reasons.append("Job is remote — location matches")
            return weight

        if not job_location:
            return weight

        # Check user's preferred locations list
        if user_locations:
            if any(loc in job_location for loc in user_locations):
                return weight
            return round(weight * 0.3)

        # Fallback: check city
        if user_city and user_city in job_location:
            return weight

        return round(weight * 0.3)

    # ── Salary scoring ─────────────────────────────────────────────────────────

    def _score_salary(
        self,
        job: Dict[str, Any],
        user_profile: Dict[str, Any],
        reasons: List[str],
    ) -> int:
        weight = _WEIGHTS["salary"]
        job_min = job.get("salary_min")
        job_max = job.get("salary_max")
        user_min = user_profile.get("desired_salary_min")
        user_max = user_profile.get("desired_salary_max")

        if job_min is None and job_max is None:
            return weight  # no salary info → full credit
        if user_min is None:
            return weight  # user hasn't set expectation

        effective_job_max = job_max or job_min

        if effective_job_max and effective_job_max >= user_min:
            return weight

        reasons.append(f"Salary ({effective_job_max}) may be below expectation ({user_min})")
        return 0

    # ── Education scoring ──────────────────────────────────────────────────────

    def _score_education(
        self,
        job: Dict[str, Any],
        user_profile: Dict[str, Any],
        reasons: List[str],
    ) -> int:
        weight = _WEIGHTS["education"]
        edu_required = (job.get("education_required") or "").lower()
        user_edu = (user_profile.get("education_level") or "").lower()

        if not edu_required:
            return weight

        _edu_rank = {"high school": 1, "diploma": 2, "bachelor": 3, "master": 4, "phd": 5, "doctorate": 5}
        required_rank = next((v for k, v in _edu_rank.items() if k in edu_required), 0)
        user_rank = next((v for k, v in _edu_rank.items() if k in user_edu), 3)  # default: bachelor

        if user_rank >= required_rank:
            return weight
        reasons.append(f"Education: job requires {edu_required}")
        return round(weight * 0.5)

    # ── Work mode scoring ──────────────────────────────────────────────────────

    def _score_work_mode(
        self,
        job: Dict[str, Any],
        user_profile: Dict[str, Any],
        reasons: List[str],
    ) -> int:
        weight = _WEIGHTS["work_mode"]
        is_remote: Optional[bool] = job.get("is_remote")
        is_hybrid: Optional[bool] = job.get("is_hybrid")
        prefers_remote: Optional[bool] = user_profile.get("prefers_remote")
        prefers_hybrid: Optional[bool] = user_profile.get("prefers_hybrid")

        if is_remote and prefers_remote:
            return weight
        if is_hybrid and (prefers_hybrid or prefers_remote):
            return weight
        if not is_remote and not is_hybrid and not prefers_remote:
            return weight  # on-site matches on-site preference
        return round(weight * 0.5)

    # ── Question answering ─────────────────────────────────────────────────────

    def answer_question(
        self,
        question: str,
        question_type: str,
        options: Optional[List[str]],
        user_profile: Dict[str, Any],
    ) -> AnswerResult:
        """
        Map a standard application question to the user's profile.
        Returns AnswerResult(answered=False) for anything that cannot be
        answered safely from profile data.

        NEVER invents information.
        """
        q = question.lower().strip()

        answer = self._try_profile_field(q, user_profile)
        if answer is not None:
            # Validate against options if this is a select/radio
            if options and question_type in ("select", "radio", "dropdown"):
                best = self._best_option(answer, options)
                if best:
                    return AnswerResult(
                        answered=True, answer=best,
                        source="local", confidence=0.95,
                        question_text=question,
                    )
                # answer doesn't match any option — need user input
                return AnswerResult(
                    answered=False, source="local",
                    question_text=question,
                    reason=(
                        f"Profile value '{answer}' does not match available "
                        f"options: {options}"
                    ),
                )
            return AnswerResult(
                answered=True, answer=str(answer),
                source="local", confidence=0.98,
                question_text=question,
            )

        # Unknown question — require user input rather than guessing
        return AnswerResult(
            answered=False,
            source="local",
            question_text=question,
            reason="Question cannot be answered from profile data — user input required",
        )

    def _try_profile_field(
        self, q: str, profile: Dict[str, Any]
    ) -> Optional[Any]:
        """
        Return the profile value for well-known question patterns.
        Returns None if the question is not recognised.
        """
        # ── Identity ──────────────────────────────────────────────────────────
        if any(x in q for x in ("first name", "firstname", "given name")):
            return profile.get("first_name")
        if any(x in q for x in ("last name", "lastname", "surname", "family name")):
            return profile.get("last_name")
        if "full name" in q:
            fn = profile.get("first_name", "")
            ln = profile.get("last_name", "")
            name = f"{fn} {ln}".strip()
            return name or None
        if "email" in q:
            return profile.get("email")
        if "phone" in q or "mobile" in q or "contact number" in q:
            return profile.get("phone")

        # ── Location ──────────────────────────────────────────────────────────
        if "city" in q:
            return profile.get("city")
        if "state" in q or "province" in q:
            return profile.get("state")
        if "country" in q:
            return profile.get("country")
        if "zip" in q or "postal" in q or "pin code" in q:
            return profile.get("zip_code")

        # ── Experience ────────────────────────────────────────────────────────
        if any(x in q for x in ("years of experience", "year of experience",
                                 "years experience", "work experience")):
            return profile.get("years_of_experience")

        # ── Professional ──────────────────────────────────────────────────────
        if any(x in q for x in ("current title", "job title", "current position",
                                 "current role", "your title")):
            return profile.get("current_title")
        if any(x in q for x in ("current company", "current employer",
                                 "company name", "employer")):
            return profile.get("current_company")
        if "linkedin" in q:
            return profile.get("linkedin_url")
        if "github" in q:
            return profile.get("github_url")
        if "portfolio" in q or "website" in q:
            return profile.get("portfolio_url") or profile.get("website_url")

        # ── Education ─────────────────────────────────────────────────────────
        if any(x in q for x in ("university", "college", "institution", "school")):
            return profile.get("university") or profile.get("college")
        if any(x in q for x in ("graduation year", "year of graduation",
                                  "graduating year", "pass out year")):
            return profile.get("graduation_year")
        if any(x in q for x in ("degree", "highest education",
                                  "highest qualification", "education level")):
            return profile.get("education_level") or profile.get("degree")
        if any(x in q for x in ("gpa", "cgpa", "grade")):
            return profile.get("gpa")

        # ── Employment preferences ─────────────────────────────────────────────
        if any(x in q for x in ("notice period", "serving notice",
                                  "notice", "joining availability")):
            np = profile.get("notice_period_days")
            if np is not None:
                if np == 0:
                    return "Immediate"
                return f"{np} days"
            return None
        if any(x in q for x in ("expected salary", "salary expectation",
                                  "desired salary", "ctc expectation",
                                  "expected ctc", "expected compensation")):
            sal = profile.get("desired_salary_min")
            sal_max = profile.get("desired_salary_max")
            currency = profile.get("salary_currency", "INR")
            if sal:
                if sal_max and sal_max != sal:
                    return f"{currency} {sal:,}–{sal_max:,}"
                return f"{currency} {sal:,}"
            return None
        if any(x in q for x in ("current salary", "current ctc",
                                  "current compensation")):
            return None  # NEVER reveal or invent current salary

        # ── Work authorization ─────────────────────────────────────────────────
        # NOTE: check sponsorship/relocation FIRST — their patterns overlap with
        # work_authorization (both contain "visa") and are more specific.
        if any(x in q for x in ("sponsorship", "require sponsorship",
                                  "visa sponsorship", "need sponsorship")):
            requires = profile.get("requires_sponsorship")
            if requires is True:
                return "Yes"
            if requires is False:
                return "No"
            return None
        if any(x in q for x in ("relocation", "relocate", "willing to relocate",
                                  "open to relocate")):
            willing = profile.get("willing_to_relocate")
            if willing is True:
                return "Yes"
            if willing is False:
                return "No"
            return None
        if any(x in q for x in ("work authorization", "work permit",
                                  "right to work", "eligible to work",
                                  "visa status", "work visa")):
            return profile.get("work_authorization")


        # ── EEO / sensitive (user-controlled, only if stored) ──────────────────
        if "gender" in q:
            return profile.get("gender")
        if "disability" in q or "disabled" in q:
            return profile.get("disability_status")
        if "veteran" in q or "military" in q:
            return profile.get("veteran_status")

        # Unknown — caller must trigger USER_INPUT_REQUIRED
        return None

    def _best_option(self, answer: str, options: List[str]) -> Optional[str]:
        """Find the best matching option for the given answer."""
        answer_lower = answer.lower()
        # Exact match
        for opt in options:
            if opt.lower() == answer_lower:
                return opt
        # Substring match
        for opt in options:
            if answer_lower in opt.lower() or opt.lower() in answer_lower:
                return opt
        return None

    # ── Job field extraction ───────────────────────────────────────────────────

    def extract_job_fields(self, raw_text: str) -> Dict[str, Any]:
        """
        Extract structured fields from a raw job description using
        regex and keyword matching. No AI API calls.
        """
        text = raw_text or ""
        text_lower = text.lower()

        # Extract skills
        skills = list(_tokenize_skills(text))

        # Extract experience range
        exp_min, exp_max = None, None
        exp_match = re.search(
            r"(\d+)\s*(?:to|-)\s*(\d+)\s*years?\s*(?:of\s*)?experience",
            text_lower
        )
        if exp_match:
            exp_min, exp_max = int(exp_match.group(1)), int(exp_match.group(2))
        else:
            exp_match = re.search(
                r"(\d+)\+?\s*years?\s*(?:of\s*)?experience",
                text_lower
            )
            if exp_match:
                exp_min = int(exp_match.group(1))

        # Work mode
        is_remote = bool(re.search(r"\bremote\b|\bwork from home\b|\bwfh\b", text_lower))
        is_hybrid = bool(re.search(r"\bhybrid\b", text_lower))

        # Employment type
        employment_type = None
        if "full-time" in text_lower or "full time" in text_lower:
            employment_type = "full-time"
        elif "part-time" in text_lower or "part time" in text_lower:
            employment_type = "part-time"
        elif "contract" in text_lower or "freelance" in text_lower:
            employment_type = "contract"
        elif "internship" in text_lower or "intern" in text_lower:
            employment_type = "internship"

        return {
            "required_skills": skills,
            "experience_min_years": exp_min,
            "experience_max_years": exp_max,
            "is_remote": is_remote,
            "is_hybrid": is_hybrid,
            "employment_type": employment_type,
        }
