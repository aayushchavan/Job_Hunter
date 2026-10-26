"""
backend/app/browser/browser_engine.py

The core browser automation engine.
Orchestrates: navigate → detect fields → fill form → (optionally) submit.

Key design decisions:
  - Always starts with is_test_run=True (no real submit unless explicitly enabled)
  - Uses Playwright async API with persistent browser context (preserves cookies/login)
  - Stealth mode to avoid bot detection
  - Keeps a human-readable step log for the UI
"""
from __future__ import annotations

import asyncio
import logging
import os
import random
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.browser.form_detector import FormDetector
from app.browser.form_filler import FillSummary, FormFiller

logger = logging.getLogger(__name__)


@dataclass
class BrowserEngineResult:
    """Full result of one browser automation run."""
    success: bool
    url: str
    fields_detected: int = 0
    fields_filled: int = 0
    questions_detected: int = 0
    answers_generated: int = 0
    resume_uploaded: bool = False
    form_validated: bool = False
    would_submit: bool = False
    submitted: bool = False
    confirmation_text: Optional[str] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    step_log: List[Dict[str, Any]] = field(default_factory=list)
    detected_fields: List[Dict[str, Any]] = field(default_factory=list)
    filled_fields: List[Dict[str, Any]] = field(default_factory=list)
    screenshot_path: Optional[str] = None


class BrowserEngine:
    """
    Playwright-based browser engine for filling job application forms.

    Usage:
        engine = BrowserEngine(settings)
        result = await engine.apply(
            url="https://example.com/apply",
            user_profile={...},
            resume_path="/path/to/resume.pdf",
            ai_provider=provider,
            is_test_run=True,      # Never submits when True
        )
    """

    def __init__(self, settings=None) -> None:
        from app.core.config import settings as cfg
        self._cfg = settings or cfg
        self._detector = FormDetector()
        self._filler = FormFiller(human_delay=True)

    async def apply(
        self,
        url: str,
        user_profile: Dict[str, Any],
        resume_path: Optional[str] = None,
        ai_provider=None,
        is_test_run: bool = True,
        auto_apply_mode: str = "safe",
    ) -> BrowserEngineResult:
        """
        Main entry point. Opens the browser, fills the form, optionally submits.

        Args:
            url: The job application URL.
            user_profile: Dict of user fields (from User model).
            resume_path: Absolute path to the resume PDF.
            ai_provider: Optional AI provider for custom question answering.
            is_test_run: If True, NEVER clicks Submit.
            auto_apply_mode: "safe" = require review before submit; "auto" = submit automatically.
        """
        step_log: List[Dict[str, Any]] = []
        result = BrowserEngineResult(success=False, url=url)

        try:
            from playwright.async_api import async_playwright

            headless = self._cfg.PLAYWRIGHT_HEADLESS
            profile_path = os.path.abspath(self._cfg.PLAYWRIGHT_BROWSER_PROFILE_PATH)
            timeout_ms = self._cfg.PLAYWRIGHT_TIMEOUT_MS

            os.makedirs(profile_path, exist_ok=True)

            async with async_playwright() as pw:
                # Use persistent context so cookies/sessions are preserved
                context = await pw.chromium.launch_persistent_context(
                    user_data_dir=profile_path,
                    headless=headless,
                    args=[
                        "--no-sandbox",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                    ],
                    viewport={"width": 1280, "height": 800},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/130.0.0.0 Safari/537.36"
                    ),
                    locale="en-US",
                    timezone_id="Asia/Kolkata",
                )

                # Apply stealth patches
                await self._apply_stealth(context)

                page = context.pages[0] if context.pages else await context.new_page()
                page.set_default_timeout(timeout_ms)

                # ── Step 1: Navigate ────────────────────────────────────────────
                self._log(step_log, "navigate", f"Opening {url}")
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                    await self._human_pause(1, 3)
                except Exception as exc:
                    return self._fail(result, step_log, "navigation_error", str(exc))

                # Handle redirects / login walls
                current_url = page.url
                self._log(step_log, "navigate", f"Landed at: {current_url}")

                # ── Step 2: Take screenshot (for review) ────────────────────────
                screenshot_dir = os.path.join(
                    os.path.abspath(self._cfg.UPLOAD_DIR), "screenshots"
                )
                os.makedirs(screenshot_dir, exist_ok=True)
                ts = int(time.time())
                screenshot_path = os.path.join(screenshot_dir, f"apply_{ts}.png")
                try:
                    await page.screenshot(path=screenshot_path, full_page=False)
                    result.screenshot_path = screenshot_path
                except Exception:
                    pass

                # ── Step 3: Detect form fields ──────────────────────────────────
                self._log(step_log, "detect", "Scanning page for form fields")
                try:
                    fields = await self._detector.detect(page)
                    # Try multi-step detection if few fields found
                    if len(fields) < 3:
                        self._log(step_log, "detect", "Few fields found, trying multi-step detection")
                        fields = await self._detector.detect_multi_step(page)
                except Exception as exc:
                    logger.warning("Field detection error: %s", exc)
                    fields = []

                result.fields_detected = len(fields)
                result.detected_fields = [f.to_dict() for f in fields]
                self._log(step_log, "detect", f"Found {len(fields)} form fields")

                if not fields:
                    result.warnings.append(
                        "No fillable form fields detected on this page. "
                        "The form may require login, use iframes, or be a multi-step wizard."
                    )

                # ── Step 4: Generate AI answers for custom questions ────────────
                ai_answers: Dict[str, str] = {}
                custom_fields = [
                    f for f in fields
                    if f.category == "custom" and f.field_type in ("text", "textarea")
                ]
                result.questions_detected = len(custom_fields)

                if ai_provider and custom_fields:
                    self._log(step_log, "ai", f"Generating answers for {len(custom_fields)} custom questions")
                    for f in custom_fields:
                        try:
                            ans = ai_provider.answer_question(
                                question=f.label or f.placeholder,
                                question_type=f.field_type,
                                options=f.options or None,
                                user_profile=user_profile,
                            )
                            if ans.answered and ans.answer:
                                ai_answers[f.name or f.label] = ans.answer
                                result.answers_generated += 1
                        except Exception as exc:
                            logger.warning("AI answer failed for '%s': %s", f.label, exc)

                # ── Step 5: Fill the form ────────────────────────────────────────
                self._log(step_log, "fill", "Filling form fields")
                fill_summary: Optional[FillSummary] = None
                try:
                    fill_summary = await self._filler.fill(
                        page=page,
                        fields=fields,
                        user_profile=user_profile,
                        ai_answers=ai_answers,
                        resume_path=resume_path,
                        is_test_run=is_test_run,
                    )
                    result.fields_filled = fill_summary.total_filled
                    result.resume_uploaded = fill_summary.resume_uploaded
                    result.warnings.extend(fill_summary.warnings)
                    result.filled_fields = [
                        {"label": r.field.label, "value": r.value_used, "source": r.source}
                        for r in fill_summary.results
                        if r.filled
                    ]
                    self._log(
                        step_log, "fill",
                        f"Filled {fill_summary.total_filled}/{fill_summary.total_detected} fields. "
                        f"Resume: {'YES' if fill_summary.resume_uploaded else 'NO'}"
                    )
                except Exception as exc:
                    logger.error("Form fill error: %s", exc, exc_info=True)
                    result.warnings.append(f"Form fill partially failed: {exc}")

                # ── Step 6: Take post-fill screenshot ───────────────────────────
                try:
                    filled_screenshot = os.path.join(screenshot_dir, f"filled_{ts}.png")
                    await page.screenshot(path=filled_screenshot, full_page=False)
                    result.screenshot_path = filled_screenshot  # use filled version
                except Exception:
                    pass

                # ── Step 7: Validate / check for errors ─────────────────────────
                self._log(step_log, "validate", "Checking for form errors")
                validation_errors = await self._check_validation_errors(page)
                if validation_errors:
                    result.warnings.extend(validation_errors)
                    self._log(step_log, "validate", f"Validation issues: {validation_errors}")
                else:
                    result.form_validated = True
                    self._log(step_log, "validate", "No visible validation errors")

                # ── Step 8: Submit (only if enabled) ────────────────────────────
                result.would_submit = not is_test_run and auto_apply_mode == "auto"

                if result.would_submit:
                    self._log(step_log, "submit", "Attempting form submission")
                    submit_result = await self._submit_form(page)
                    if submit_result["submitted"]:
                        result.submitted = True
                        result.confirmation_text = submit_result.get("confirmation")
                        self._log(step_log, "submit", f"Submitted! Confirmation: {result.confirmation_text}")
                    else:
                        result.warnings.append(f"Submit failed: {submit_result.get('error')}")
                        self._log(step_log, "submit", f"Submit failed: {submit_result.get('error')}")
                else:
                    reason = "test_run" if is_test_run else "safe_mode_requires_review"
                    self._log(step_log, "submit", f"Skipped submission ({reason})")

                result.success = True
                await context.close()

        except Exception as exc:
            error_type = type(exc).__name__
            tb = traceback.format_exc()
            logger.error("BrowserEngine.apply crashed: %s\n%s", exc, tb)
            return self._fail(result, step_log, error_type, str(exc)[:500])

        result.step_log = step_log
        return result

    # ── Helpers ────────────────────────────────────────────────────────────────

    async def _apply_stealth(self, context) -> None:
        """Override navigator.webdriver and other bot-detection fingerprints."""
        stealth_js = """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3]});
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        window.chrome = {runtime: {}};
        """
        try:
            await context.add_init_script(stealth_js)
        except Exception as exc:
            logger.debug("Stealth script failed (non-fatal): %s", exc)

    async def _check_validation_errors(self, page) -> List[str]:
        """Look for visible error messages on the page."""
        error_selectors = [
            ".error",
            ".field-error",
            "[aria-invalid='true']",
            ".invalid-feedback",
            ".form-error",
            "[data-error]",
            ".alert-danger",
        ]
        errors: List[str] = []
        for sel in error_selectors:
            try:
                elements = page.locator(sel)
                count = await elements.count()
                for i in range(min(count, 5)):
                    text = (await elements.nth(i).text_content() or "").strip()
                    if text and len(text) < 200:
                        errors.append(text)
            except Exception:
                pass
        return list(set(errors))[:10]

    async def _submit_form(self, page) -> Dict[str, Any]:
        """Find and click the submit button. Returns {submitted, confirmation, error}."""
        submit_selectors = [
            "button[type='submit']",
            "input[type='submit']",
            "button:has-text('Submit')",
            "button:has-text('Apply')",
            "button:has-text('Send Application')",
            "[data-testid*='submit']",
            "[aria-label*='submit']",
        ]
        for sel in submit_selectors:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible():
                    await btn.click()
                    await self._human_pause(2, 4)
                    # Check for confirmation
                    conf = await self._detect_confirmation(page)
                    return {"submitted": True, "confirmation": conf}
            except Exception as exc:
                logger.debug("Submit selector %s failed: %s", sel, exc)
        return {"submitted": False, "error": "No submit button found"}

    async def _detect_confirmation(self, page) -> Optional[str]:
        """Try to extract a confirmation message after submission."""
        confirmation_selectors = [
            ".confirmation",
            ".success",
            "[class*='success']",
            "[class*='confirm']",
            "h1:has-text('Thank')",
            "h2:has-text('Thank')",
            "p:has-text('successfully')",
            "p:has-text('received')",
        ]
        for sel in confirmation_selectors:
            try:
                el = page.locator(sel).first
                if await el.is_visible():
                    return (await el.text_content() or "").strip()[:500]
            except Exception:
                pass
        return None

    @staticmethod
    async def _human_pause(min_s: float, max_s: float) -> None:
        await asyncio.sleep(min_s + random.random() * (max_s - min_s))

    @staticmethod
    def _log(log: List[Dict], step: str, message: str) -> None:
        log.append({
            "step": step,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        logger.info("[%s] %s", step.upper(), message)

    @staticmethod
    def _fail(
        result: BrowserEngineResult,
        step_log: List[Dict],
        error_type: str,
        error_message: str,
    ) -> BrowserEngineResult:
        result.success = False
        result.error_type = error_type
        result.error_message = error_message
        result.step_log = step_log
        return result


# ── Module-level singleton ─────────────────────────────────────────────────────
browser_engine = BrowserEngine()
