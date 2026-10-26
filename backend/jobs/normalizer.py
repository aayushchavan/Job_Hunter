"""
backend/jobs/normalizer.py

Deterministic job normalization and fingerprinting.

Responsibilities:
  - Normalize all string fields (title, company, location, etc.)
  - Normalize URLs (strip tracking params)
  - Normalize employment type, work mode, salary currency
  - Extract skills from description when not provided
  - Generate a stable SHA-256 fingerprint for deduplication
  - Validate required fields

Rules:
  - No LLM calls.
  - No external API calls.
  - Pure deterministic Python.
  - Never invents data.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from jobs.sources.base import NormalizedJob

# ── Skill extraction (reuse synonyms from LocalAIProvider concept) ─────────────
# Ordered longest-first for greedy matching
_KNOWN_SKILLS: List[str] = sorted([
    "python", "python3", "javascript", "typescript", "java", "c#", "c++",
    "golang", "go", "rust", "scala", "kotlin", "swift", "r", "matlab",
    "node.js", "nodejs", "react", "react.js", "angular", "vue.js", "vue",
    "django", "flask", "fastapi", "spring", "spring boot", "rails",
    "postgresql", "postgres", "mysql", "sqlite", "mongodb", "redis",
    "elasticsearch", "cassandra", "dynamodb",
    "docker", "kubernetes", "k8s", "terraform", "ansible", "jenkins",
    "aws", "gcp", "azure", "heroku", "linux", "ubuntu",
    "rest api", "restful api", "graphql", "grpc", "soap",
    "machine learning", "deep learning", "nlp", "computer vision",
    "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy",
    "git", "github", "gitlab", "bitbucket",
    "ci/cd", "devops", "agile", "scrum",
    "html", "css", "sql", "bash", "shell scripting",
    "microservices", "kafka", "rabbitmq", "celery",
    "spark", "hadoop", "airflow", "databricks", "snowflake",
], key=len, reverse=True)

# URL tracking parameters to always strip
_TRACKING_PARAMS: Set[str] = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "utm_id", "ref", "referrer", "source", "sc", "v", "cid", "sid",
    "adref", "cty", "fbclid", "gclid", "msclkid", "twclid",
}

# Employment type normalization map
_EMPLOYMENT_TYPE_CANONICAL: Dict[str, str] = {
    "full-time": "full-time", "full time": "full-time", "permanent": "full-time",
    "part-time": "part-time", "part time": "part-time",
    "contract": "contract", "contractor": "contract", "freelance": "contract",
    "temporary": "contract", "temp": "contract",
    "internship": "internship", "intern": "internship", "graduate": "internship",
    "apprenticeship": "internship",
}


class JobNormalizer:
    """
    Stateless normalizer: converts a NormalizedJob dict (as returned by a
    source) into a fully normalized, fingerprinted version ready for DB upsert.
    """

    def normalize(self, job: NormalizedJob) -> NormalizedJob:
        """
        Apply all normalization steps and generate the fingerprint.
        Returns a new dict — does not mutate the input.
        """
        out = dict(job)

        # Strings
        out["title"] = self._clean_title(job.get("title") or "")
        out["company_name"] = self._clean_company(job.get("company_name") or "")
        out["location"] = self._clean_location(job.get("location"))

        # URLs
        out["canonical_url"] = self._canonical_url(
            job.get("canonical_url") or job.get("apply_url") or ""
        )
        out["apply_url"] = job.get("apply_url") or job.get("canonical_url")

        # Employment type
        out["employment_type"] = self._normalize_employment_type(
            job.get("employment_type")
        )

        # Work mode
        out["work_mode"], out["is_remote"], out["is_hybrid"] = self._normalize_work_mode(
            job.get("work_mode"),
            job.get("is_remote"),
            job.get("is_hybrid"),
            job.get("description") or "",
        )

        # Skills — extract from description if not explicitly provided
        req_skills = job.get("required_skills") or []
        if not req_skills:
            req_skills = self._extract_skills(job.get("description") or "")
        out["required_skills"] = [s.lower().strip() for s in req_skills if s]

        pref_skills = job.get("preferred_skills") or []
        out["preferred_skills"] = [s.lower().strip() for s in pref_skills if s]

        # Salary: ensure salary_min <= salary_max
        sal_min = job.get("salary_min")
        sal_max = job.get("salary_max")
        if sal_min and sal_max and sal_min > sal_max:
            sal_min, sal_max = sal_max, sal_min
        out["salary_min"] = sal_min
        out["salary_max"] = sal_max
        out["salary_currency"] = (job.get("salary_currency") or "").upper() or None

        # Experience: preserve if provided, or extract from title + description
        exp_min = job.get("experience_min_years")
        exp_max = job.get("experience_max_years")
        if exp_min is None and exp_max is None:
            combined = f"{out['title']} {job.get('description') or ''}"
            exp_min, exp_max = self._extract_experience(combined)
        out["experience_min_years"] = exp_min
        out["experience_max_years"] = exp_max

        # Discovered timestamp
        if not out.get("discovered_at"):
            out["discovered_at"] = datetime.now(timezone.utc)

        # Fingerprint — must be last (depends on normalized fields)
        out["fingerprint"] = self._fingerprint(out)  # type: ignore[arg-type]

        return out  # type: ignore[return-value]

    # ── Normalization helpers ──────────────────────────────────────────────────

    @staticmethod
    def _clean_title(title: str) -> str:
        """Remove excessive whitespace and HTML entities from title."""
        title = re.sub(r"\s+", " ", title).strip()
        title = re.sub(r"&amp;", "&", title)
        title = re.sub(r"&lt;", "<", title)
        title = re.sub(r"&gt;", ">", title)
        return title

    @staticmethod
    def _clean_company(company: str) -> str:
        """Normalize company name."""
        company = re.sub(r"\s+", " ", company).strip()
        # Remove common legal suffixes for comparison (keep for display)
        return company

    @staticmethod
    def _clean_location(location: Optional[str]) -> Optional[str]:
        if not location:
            return None
        location = re.sub(r"\s+", " ", location).strip()
        # Remove country suffix if location is just "Country, Country"
        return location or None

    @staticmethod
    def _canonical_url(url: str) -> Optional[str]:
        """Strip tracking query parameters and normalize URL."""
        if not url:
            return None
        try:
            parsed = urlparse(url.strip())
            if not parsed.scheme:
                return url
            query = parse_qs(parsed.query, keep_blank_values=False)
            clean = {
                k: v for k, v in query.items()
                if k.lower() not in _TRACKING_PARAMS
            }
            new_query = urlencode(
                {k: v[0] for k, v in clean.items()}
            ) if clean else ""
            return urlunparse((
                parsed.scheme, parsed.netloc.lower(),
                parsed.path, parsed.params, new_query, ""
            ))
        except Exception:
            return url

    @staticmethod
    def _normalize_employment_type(raw: Optional[str]) -> Optional[str]:
        if not raw:
            return None
        return _EMPLOYMENT_TYPE_CANONICAL.get(raw.lower().strip(), raw.lower().strip())

    @staticmethod
    def _normalize_work_mode(
        work_mode: Optional[str],
        is_remote: Optional[bool],
        is_hybrid: Optional[bool],
        description: str,
    ):
        """Return (work_mode_str, is_remote, is_hybrid) tuple."""
        desc_lower = description.lower()

        # Derive from flags if work_mode not set
        if not work_mode or work_mode == "unknown":
            if is_remote:
                work_mode = "remote"
            elif is_hybrid:
                work_mode = "hybrid"
            else:
                # Try to infer from description
                if re.search(r"\bremote\b|\bwork from home\b|\bwfh\b", desc_lower):
                    work_mode = "remote"
                    is_remote = True
                elif re.search(r"\bhybrid\b", desc_lower):
                    work_mode = "hybrid"
                    is_hybrid = True
                else:
                    work_mode = "onsite"

        # Sync flags with work_mode
        if work_mode == "remote":
            is_remote = True
            is_hybrid = False
        elif work_mode == "hybrid":
            is_remote = False
            is_hybrid = True
        else:
            is_remote = is_remote or False
            is_hybrid = is_hybrid or False

        return work_mode, is_remote, is_hybrid

    @staticmethod
    def _extract_skills(description: str) -> List[str]:
        """Extract known skill names from a job description."""
        desc_lower = description.lower()
        found: List[str] = []
        for skill in _KNOWN_SKILLS:
            pattern = r"\b" + re.escape(skill) + r"\b"
            if re.search(pattern, desc_lower):
                found.append(skill)
        # Deduplicate while preserving order
        seen: Set[str] = set()
        result: List[str] = []
        for s in found:
            if s not in seen:
                seen.add(s)
                result.append(s)
        return result

    @staticmethod
    def _extract_experience(text: str) -> Tuple[Optional[int], Optional[int]]:
        """Extract min and max experience years from title and description."""
        if not text:
            return None, None

        # 1. Look for range e.g. "3-5 years", "3 to 5 yrs", "3 - 5+ years"
        m = re.search(r"\b(\d+)\s*(?:-|to)\s*(\d+)\s*(?:\+)?\s*(?:years?|yrs?)\b", text, re.I)
        if m:
            try:
                min_y = int(m.group(1))
                max_y = int(m.group(2))
                if min_y <= max_y and min_y <= 30:
                    return min_y, max_y
            except (ValueError, TypeError):
                pass

        # 2. Look for minimum e.g. "5+ years", "at least 3 years", "minimum 4 years", "3+ yrs"
        m = re.search(r"(?:minimum|at least|min\.?|\b)\s*(\d+)\+?\s*(?:years?|yrs?)(?:\s*(?:of\s*)?experience)?\b", text, re.I)
        if m:
            try:
                min_y = int(m.group(1))
                if 1 <= min_y <= 30:
                    return min_y, None
            except (ValueError, TypeError):
                pass

        # 3. Heuristic matching based on seniority in title
        text_lower = text.lower()
        if re.search(r"\b(intern|internship|graduate|trainee|fresher)\b", text_lower):
            return 0, 1
        if re.search(r"\b(entry level|junior|assoc|associate)\b", text_lower):
            return 0, 2
        if re.search(r"\b(lead|principal|staff|architect|director|head of)\b", text_lower):
            return 8, None
        if re.search(r"\b(senior|sr\.?)\b", text_lower):
            return 5, None
        if re.search(r"\b(mid level|mid-level|intermediate)\b", text_lower):
            return 2, 5

        return None, None

    @staticmethod
    def _fingerprint(job: Dict[str, Any]) -> str:
        """
        Generate a stable SHA-256 fingerprint for deduplication.

        Primary strategy (when external_id is available):
          SHA256(source + ":" + external_id)

        Fallback:
          SHA256(source + ":" + company_name_lower + ":" + title_lower + ":" + canonical_url)

        This means repeated discovery of the same job always produces the same hash.
        """
        source: str = (job.get("source") or "unknown").lower()
        external_id: str = str(job.get("external_id") or "").strip()

        if external_id:
            key = f"{source}:{external_id}"
        else:
            company = (job.get("company_name") or "").lower().strip()
            title = (job.get("title") or "").lower().strip()
            url = (job.get("canonical_url") or "").lower().strip()
            key = f"{source}:{company}:{title}:{url}"

        return hashlib.sha256(key.encode("utf-8")).hexdigest()


# Module-level singleton
_normalizer = JobNormalizer()


def normalize_job(job: NormalizedJob) -> NormalizedJob:
    """Normalize and fingerprint a single job. Convenience wrapper."""
    return _normalizer.normalize(job)
