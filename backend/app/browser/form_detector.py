"""
backend/app/browser/form_detector.py

Form field detection and classification using DOM analysis + AI.
Extracts all fillable fields from a job application page.
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class FormField:
    """Represents a single detected form field."""
    selector: str            # CSS selector to locate this field
    field_type: str          # text | email | tel | textarea | select | checkbox | radio | file
    label: str               # Human-readable label text
    name: str                # HTML name attribute
    placeholder: str = ""
    required: bool = False
    options: List[str] = field(default_factory=list)  # for select/radio
    value: Optional[str] = None    # current value if pre-filled
    category: str = "unknown"      # personal | contact | work | education | upload | consent | custom

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selector": self.selector,
            "field_type": self.field_type,
            "label": self.label,
            "name": self.name,
            "placeholder": self.placeholder,
            "required": self.required,
            "options": self.options,
            "value": self.value,
            "category": self.category,
        }


# ── Keyword-based category classifier ─────────────────────────────────────────

_CATEGORY_PATTERNS: Dict[str, List[str]] = {
    "personal": [
        "first.?name", "last.?name", "full.?name", "given.?name", "surname",
        "gender", "dob", "date.?of.?birth", "age",
    ],
    "contact": [
        "email", "phone", "mobile", "tel", "address", "city", "state",
        "zip", "postal", "country", "location",
    ],
    "work": [
        "title", "position", "role", "company", "employer", "salary",
        "experience", "years", "notice", "start.?date", "availability",
        "work.?auth", "authorization", "sponsor", "visa", "reloc",
        "linkedin", "github", "portfolio", "website", "url",
    ],
    "education": [
        "degree", "university", "college", "school", "gpa", "graduation",
        "major", "field.?of.?study",
    ],
    "upload": [
        "resume", "cv", "cover.?letter", "attachment", "upload", "file",
    ],
    "consent": [
        "agree", "consent", "terms", "privacy", "gdpr", "eeo", "diversity",
        "veteran", "disability",
    ],
}


def classify_field(label: str, name: str, placeholder: str) -> str:
    """Classify a field into a category based on its label/name/placeholder text."""
    text = f"{label} {name} {placeholder}".lower()
    for category, patterns in _CATEGORY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text):
                return category
    return "custom"


# ── DOM extraction script (runs inside browser) ────────────────────────────────

_EXTRACT_FIELDS_JS = """
() => {
    const fields = [];
    const seen = new Set();

    function getLabel(el) {
        // 1. aria-label
        if (el.getAttribute('aria-label')) return el.getAttribute('aria-label').trim();
        // 2. <label for="id">
        const id = el.getAttribute('id');
        if (id) {
            const lbl = document.querySelector(`label[for="${id}"]`);
            if (lbl) return lbl.textContent.trim();
        }
        // 3. Closest <label> wrapper
        const wrapper = el.closest('label');
        if (wrapper) return wrapper.textContent.replace(el.value || '', '').trim();
        // 4. aria-labelledby
        const lblId = el.getAttribute('aria-labelledby');
        if (lblId) {
            const lbl = document.getElementById(lblId);
            if (lbl) return lbl.textContent.trim();
        }
        // 5. Preceding <label> sibling
        let prev = el.previousElementSibling;
        while (prev) {
            if (prev.tagName === 'LABEL') return prev.textContent.trim();
            if (prev.querySelector('label')) return prev.querySelector('label').textContent.trim();
            prev = prev.previousElementSibling;
        }
        // 6. Parent text
        const parent = el.parentElement;
        if (parent) {
            const txt = parent.textContent.trim().replace(el.value || '', '');
            if (txt.length < 80) return txt;
        }
        return el.getAttribute('name') || el.getAttribute('placeholder') || '';
    }

    function makeSelector(el) {
        if (el.id) return `#${CSS.escape(el.id)}`;
        if (el.name) return `[name="${CSS.escape(el.name)}"]`;
        // Build a path
        const path = [];
        let cur = el;
        while (cur && cur.tagName) {
            let seg = cur.tagName.toLowerCase();
            if (cur.id) { path.unshift(`#${CSS.escape(cur.id)}`); break; }
            const idx = Array.from(cur.parentElement?.children || []).indexOf(cur);
            if (idx > -1) seg += `:nth-child(${idx + 1})`;
            path.unshift(seg);
            cur = cur.parentElement;
        }
        return path.join(' > ');
    }

    // ── Inputs ─────────────────────────────────────────────────────────────────
    document.querySelectorAll('input, textarea, select').forEach(el => {
        const type = (el.getAttribute('type') || el.tagName.toLowerCase()).toLowerCase();
        if (['hidden', 'submit', 'button', 'reset', 'image'].includes(type)) return;
        if (el.disabled || el.readOnly) return;

        const sel = makeSelector(el);
        if (seen.has(sel)) return;
        seen.add(sel);

        const label = getLabel(el);

        let options = [];
        if (el.tagName === 'SELECT') {
            options = Array.from(el.options)
                .filter(o => o.value !== '' && o.value !== null)
                .map(o => o.text.trim());
        }
        // Radio/checkbox groups
        if (type === 'radio' && el.name) {
            options = Array.from(
                document.querySelectorAll(`input[type="radio"][name="${CSS.escape(el.name)}"]`)
            ).map(r => r.getAttribute('value') || getLabel(r)).filter(Boolean);
        }

        fields.push({
            selector: sel,
            field_type: el.tagName === 'SELECT' ? 'select' : (el.tagName === 'TEXTAREA' ? 'textarea' : type),
            label: label,
            name: el.getAttribute('name') || '',
            placeholder: el.getAttribute('placeholder') || '',
            required: el.required || el.getAttribute('aria-required') === 'true',
            options: options,
            value: el.value || null,
        });
    });

    return fields;
}
"""


class FormDetector:
    """
    Detects and classifies form fields on a job application page.
    Uses DOM inspection via Playwright + keyword-based classification.
    """

    async def detect(self, page) -> List[FormField]:
        """
        Extract all fillable form fields from the current page.
        Returns a list of FormField objects.
        """
        try:
            raw = await page.evaluate(_EXTRACT_FIELDS_JS)
        except Exception as exc:
            logger.warning("JS field extraction failed: %s", exc)
            raw = []

        fields: List[FormField] = []
        seen_names: set[str] = set()

        for item in raw:
            name = item.get("name", "")
            label = item.get("label", "")
            placeholder = item.get("placeholder", "")

            # De-duplicate radio groups (keep only first representative)
            if item.get("field_type") == "radio" and name in seen_names:
                continue
            if name:
                seen_names.add(name)

            category = classify_field(label, name, placeholder)

            fields.append(FormField(
                selector=item["selector"],
                field_type=item["field_type"],
                label=label,
                name=name,
                placeholder=placeholder,
                required=item.get("required", False),
                options=item.get("options", []),
                value=item.get("value"),
                category=category,
            ))

        logger.info("Detected %d form fields on page", len(fields))
        return fields

    async def detect_multi_step(self, page, max_steps: int = 5) -> List[FormField]:
        """
        For multi-page/step forms: detect fields across multiple Next button clicks.
        Returns cumulative field list.
        """
        all_fields: List[FormField] = []
        visited_pages: set[str] = set()

        for step in range(max_steps):
            url = page.url
            if url in visited_pages:
                break
            visited_pages.add(url)

            step_fields = await self.detect(page)
            all_fields.extend(step_fields)
            logger.info("Step %d: detected %d fields", step + 1, len(step_fields))

            # Try to find a "Next" button
            next_btn = await self._find_next_button(page)
            if not next_btn:
                break

            try:
                await next_btn.click()
                await page.wait_for_load_state("domcontentloaded", timeout=5000)
                await asyncio.sleep(1)
            except Exception:
                break

        return all_fields

    async def _find_next_button(self, page):
        """Find the 'Next' / 'Continue' button on a multi-step form."""
        selectors = [
            "button:has-text('Next')",
            "button:has-text('Continue')",
            "button:has-text('Proceed')",
            "input[type='button'][value*='Next']",
            "[data-testid*='next']",
            "[aria-label*='next']",
        ]
        for sel in selectors:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible():
                    return btn
            except Exception:
                pass
        return None
