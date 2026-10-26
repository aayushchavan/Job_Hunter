"""
backend/app/browser/form_filler.py

Intelligent form filler.
Maps detected form fields → user profile values → Playwright fill actions.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.browser.form_detector import FormField

logger = logging.getLogger(__name__)


@dataclass
class FillResult:
    """Result of filling a single field."""
    field: FormField
    filled: bool
    value_used: Optional[str]
    source: str        # "profile" | "ai" | "skipped" | "error"
    error: Optional[str] = None


@dataclass
class FillSummary:
    """Summary of a complete form-fill attempt."""
    total_detected: int
    total_filled: int
    total_skipped: int
    total_errors: int
    resume_uploaded: bool
    results: List[FillResult] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def fill_rate(self) -> float:
        if self.total_detected == 0:
            return 0.0
        return self.total_filled / self.total_detected


# ── Profile → field value mapping ─────────────────────────────────────────────

def _profile_value_for_field(
    f: FormField,
    user_profile: Dict[str, Any],
    resume_path: Optional[str] = None,
) -> Optional[str]:
    """
    Try to find a value for the field from the user profile.
    Returns None if no direct match found.
    """
    label_lower = f"{f.label} {f.name} {f.placeholder}".lower()

    # Personal
    if _match(label_lower, ["first.?name", "given.?name", "fname"]):
        return user_profile.get("first_name")
    if _match(label_lower, ["last.?name", "surname", "family.?name", "lname"]):
        return user_profile.get("last_name")
    if _match(label_lower, ["full.?name", "your.?name", "name"]):
        fn = user_profile.get("first_name", "")
        ln = user_profile.get("last_name", "")
        return f"{fn} {ln}".strip() or None

    # Contact
    if _match(label_lower, ["email", "e-mail"]):
        return user_profile.get("email")
    if _match(label_lower, ["phone", "mobile", "tel", "contact.?number"]):
        return user_profile.get("phone")

    # Location
    if _match(label_lower, ["city"]):
        return user_profile.get("city")
    if _match(label_lower, ["state", "province"]):
        return user_profile.get("state")
    if _match(label_lower, ["country"]):
        return user_profile.get("country")
    if _match(label_lower, ["zip", "postal", "pin.?code"]):
        return user_profile.get("zip_code")
    if _match(label_lower, ["address", "street"]):
        return user_profile.get("city")  # best we can do without full street

    # Professional
    if _match(label_lower, ["current.?title", "job.?title", "position", "designation"]):
        return user_profile.get("current_title")
    if _match(label_lower, ["current.?company", "employer", "organization"]):
        return user_profile.get("current_company")
    if _match(label_lower, ["years.?of.?exp", "experience", "total.?exp"]):
        yoe = user_profile.get("years_of_experience")
        return str(yoe) if yoe is not None else None
    if _match(label_lower, ["linkedin"]):
        return user_profile.get("linkedin_url")
    if _match(label_lower, ["github"]):
        return user_profile.get("github_url")
    if _match(label_lower, ["portfolio", "website", "personal.?site"]):
        return user_profile.get("portfolio_url") or user_profile.get("website_url")

    # Salary
    if _match(label_lower, ["salary", "ctc", "compensation", "expected"]):
        sal = user_profile.get("desired_salary_min")
        return str(sal) if sal else None

    # Work authorization
    if _match(label_lower, ["work.?auth", "authorized", "eligible.?to.?work"]):
        return user_profile.get("work_authorization")
    if _match(label_lower, ["sponsor", "visa.?sponsor"]):
        req = user_profile.get("requires_sponsorship")
        if req is not None:
            return "Yes" if req else "No"
    if _match(label_lower, ["reloc", "willing.?to.?reloc"]):
        rel = user_profile.get("willing_to_relocate")
        if rel is not None:
            return "Yes" if rel else "No"
    if _match(label_lower, ["notice", "notice.?period"]):
        np = user_profile.get("notice_period_days")
        return str(np) if np else None

    # EEO / Diversity (only fill if user has provided — never fabricate)
    if _match(label_lower, ["gender", "sex"]):
        return user_profile.get("gender")
    if _match(label_lower, ["veteran"]):
        return user_profile.get("veteran_status")
    if _match(label_lower, ["disability"]):
        return user_profile.get("disability_status")

    # Summary / Cover letter
    if _match(label_lower, ["summary", "about.?you", "tell.?us", "cover.?letter", "motivation"]):
        return user_profile.get("summary")

    return None


def _match(text: str, patterns: List[str]) -> bool:
    return any(re.search(p, text, re.I) for p in patterns)


def _best_option_match(value: str, options: List[str]) -> Optional[str]:
    """
    Find the best matching option from a select/radio list.
    First tries exact match, then substring, then fuzzy.
    """
    if not options or not value:
        return None
    val_lower = value.lower()

    # Exact match
    for opt in options:
        if opt.lower() == val_lower:
            return opt

    # Substring match
    for opt in options:
        if val_lower in opt.lower() or opt.lower() in val_lower:
            return opt

    # Word overlap
    val_words = set(val_lower.split())
    best, best_score = None, 0
    for opt in options:
        words = set(opt.lower().split())
        score = len(val_words & words)
        if score > best_score:
            best, best_score = opt, score

    return best if best_score > 0 else None


# ── Main filler ────────────────────────────────────────────────────────────────

class FormFiller:
    """
    Fills a job application form using Playwright.
    Accepts a list of FormField objects and a user profile dict.
    """

    def __init__(self, human_delay: bool = True) -> None:
        self._human_delay = human_delay  # simulate human typing

    async def fill(
        self,
        page,
        fields: List[FormField],
        user_profile: Dict[str, Any],
        ai_answers: Optional[Dict[str, str]] = None,  # field_name → answer from AI
        resume_path: Optional[str] = None,
        is_test_run: bool = True,
    ) -> FillSummary:
        """
        Fill all detected fields.
        - Direct profile values are used where possible.
        - AI-generated answers are used for custom questions.
        - File inputs with resume are handled separately.
        - Consent/terms checkboxes are always checked.
        """
        results: List[FillResult] = []
        warnings: List[str] = []
        resume_uploaded = False
        ai_answers = ai_answers or {}

        for f in fields:
            result = await self._fill_field(
                page, f, user_profile, ai_answers, resume_path, is_test_run
            )
            results.append(result)
            if result.error:
                warnings.append(f"Field '{f.label}': {result.error}")

            if result.filled and f.field_type == "file":
                resume_uploaded = True

            # Small human-like delay between fields
            if self._human_delay and result.filled:
                await asyncio.sleep(0.3 + (hash(f.selector) % 7) * 0.1)

        filled = [r for r in results if r.filled]
        errors = [r for r in results if r.error]
        skipped = [r for r in results if not r.filled and not r.error]

        return FillSummary(
            total_detected=len(fields),
            total_filled=len(filled),
            total_skipped=len(skipped),
            total_errors=len(errors),
            resume_uploaded=resume_uploaded,
            results=results,
            warnings=warnings,
        )

    async def _fill_field(
        self,
        page,
        f: FormField,
        user_profile: Dict[str, Any],
        ai_answers: Dict[str, str],
        resume_path: Optional[str],
        is_test_run: bool,
    ) -> FillResult:
        try:
            locator = page.locator(f.selector).first

            # Check visibility
            try:
                visible = await locator.is_visible(timeout=2000)
                if not visible:
                    return FillResult(f, False, None, "skipped", "Field not visible")
            except Exception:
                return FillResult(f, False, None, "skipped", "Locator not found")

            # ── File upload (resume) ───────────────────────────────────────────
            if f.field_type == "file":
                if resume_path and os.path.exists(resume_path):
                    await locator.set_input_files(resume_path)
                    logger.info("Uploaded resume: %s", resume_path)
                    return FillResult(f, True, resume_path, "profile")
                else:
                    return FillResult(f, False, None, "skipped", "No resume file available")

            # ── Checkbox (consent / agree) ─────────────────────────────────────
            if f.field_type == "checkbox":
                label_lower = f"{f.label} {f.name}".lower()
                is_consent = any(w in label_lower for w in [
                    "agree", "consent", "terms", "privacy", "accept", "gdpr"
                ])
                if is_consent:
                    checked = await locator.is_checked()
                    if not checked:
                        await locator.check()
                    return FillResult(f, True, "checked", "profile")
                return FillResult(f, False, None, "skipped", "Non-consent checkbox — skipped")

            # ── Determine value to fill ────────────────────────────────────────
            value = _profile_value_for_field(f, user_profile, resume_path)

            # Fall back to AI answer
            if value is None and f.name in ai_answers:
                value = ai_answers[f.name]
                source = "ai"
            elif value is None and f.label in ai_answers:
                value = ai_answers[f.label]
                source = "ai"
            else:
                source = "profile"

            if value is None:
                return FillResult(f, False, None, "skipped", "No value available")

            # ── Select field ───────────────────────────────────────────────────
            if f.field_type == "select":
                best = _best_option_match(value, f.options)
                if best:
                    await locator.select_option(label=best)
                    return FillResult(f, True, best, source)
                # Try selecting by value string directly
                try:
                    await locator.select_option(value=value)
                    return FillResult(f, True, value, source)
                except Exception:
                    return FillResult(f, False, value, "skipped", f"No matching option for '{value}'")

            # ── Radio ──────────────────────────────────────────────────────────
            if f.field_type == "radio":
                best = _best_option_match(value, f.options)
                if best:
                    radio_sel = f"input[type='radio'][name='{f.name}']"
                    try:
                        # Try to click the radio with matching value or label
                        radio = page.locator(
                            f"input[type='radio'][name='{f.name}'][value='{best}']"
                        ).first
                        if await radio.count() > 0:
                            await radio.check()
                            return FillResult(f, True, best, source)
                    except Exception:
                        pass
                return FillResult(f, False, value, "skipped", "Could not locate radio option")

            # ── Text / email / tel / textarea ──────────────────────────────────
            await locator.click()
            await locator.clear()
            if self._human_delay:
                await self._human_type(locator, str(value))
            else:
                await locator.fill(str(value))

            return FillResult(f, True, str(value), source)

        except Exception as exc:
            logger.warning("Error filling field '%s': %s", f.label, exc)
            return FillResult(f, False, None, "error", str(exc)[:200])

    async def _human_type(self, locator, text: str) -> None:
        """Type text character by character with small random delays (anti-bot)."""
        import random
        for char in text:
            await locator.type(char, delay=random.randint(30, 80))
