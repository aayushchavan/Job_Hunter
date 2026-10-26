"""
backend/app/ai/gemini_provider.py

GeminiAIProvider — Google Gemini-based implementation of AIProvider.

THIS MODULE IS NEVER IMPORTED when AI_PROVIDER=local.
The factory (factory.py) is the only code that imports this.

Free tier (as of 2024):
  - gemini-1.5-flash: 1,500 req/day, 1M tokens/min — FREE
  - gemini-2.0-flash: 1,500 req/day — FREE

Requires:
  pip install google-generativeai
  AI_PROVIDER=gemini
  GEMINI_API_KEY=<your-key from https://aistudio.google.com/app/apikey>
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from app.ai.base import AIProvider, AnswerResult, MatchResult


class GeminiAIProvider(AIProvider):
    """
    AI provider backed by Google Gemini.
    Only instantiated when AI_PROVIDER=gemini.

    Uses structured JSON prompts identical in intent to the Claude provider,
    so the response format is consistent across providers.
    """

    def __init__(self, api_key: str, model: str) -> None:
        import warnings
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=FutureWarning)
            try:
                import google.generativeai as genai  # noqa: F401
            except ImportError as exc:
                raise ImportError(
                    "The 'google-generativeai' package is not installed. "
                    "Run: pip install google-generativeai"
                ) from exc

        import google.generativeai as genai
        genai.configure(api_key=api_key, transport="rest")
        self._model = genai.GenerativeModel(
            model_name=model,
            generation_config={
                "temperature": 0.1,          # low temp = consistent, factual answers
                "response_mime_type": "application/json",  # force JSON output
            },
        )
        self._model_name = model
        self._rate_limited_until: float = 0.0

    @property
    def provider_name(self) -> str:
        return "gemini"

    # ── Job match scoring ──────────────────────────────────────────────────────

    def score_job_match(
        self,
        job: Dict[str, Any],
        user_profile: Dict[str, Any],
    ) -> MatchResult:
        """
        Ask Gemini to score how well the candidate matches the job.
        Returns a structured MatchResult with score 0–100.
        """
        prompt = (
            "You are a precise job-matching assistant. Score how well the candidate "
            "profile matches the job. Return ONLY a valid JSON object with these exact fields:\n"
            "  score: integer 0-100\n"
            "  matched_skills: list of skills the candidate has that the job needs\n"
            "  missing_skills: list of skills the job needs that the candidate lacks\n"
            "  reasons: list of short strings explaining the score\n"
            "  breakdown: object with keys role, experience, required_skills, "
            "preferred_skills, location, salary, education, work_mode — "
            "each value is an integer (must sum to score)\n\n"
            "RULES:\n"
            "- Never invent skills the candidate doesn't have\n"
            "- Score honestly even if it hurts\n"
            "- Return ONLY valid JSON, no markdown, no explanation\n\n"
            f"JOB:\n{json.dumps(job, default=str, indent=2)}\n\n"
            f"CANDIDATE PROFILE:\n{json.dumps(user_profile, default=str, indent=2)}"
        )

        data = self._call(prompt)
        if not data or not data.get("score"):
            from app.ai.local_provider import LocalAIProvider
            return LocalAIProvider().score_job_match(job, user_profile)

        return MatchResult(
            score=min(100, max(0, int(data.get("score", 0)))),
            matched_skills=data.get("matched_skills", []),
            missing_skills=data.get("missing_skills", []),
            reasons=data.get("reasons", []),
            breakdown=data.get("breakdown", {}),
        )

    # ── Question answering ─────────────────────────────────────────────────────

    def answer_question(
        self,
        question: str,
        question_type: str,
        options: Optional[List[str]],
        user_profile: Dict[str, Any],
    ) -> AnswerResult:
        """
        Answer a single application form question using the candidate profile.
        Never invents information — returns answered=false if unsure.
        """
        options_section = f"\nAvailable options: {json.dumps(options)}" if options else ""
        prompt = (
            "You are filling in a job application form on behalf of the candidate. "
            "Answer the question ONLY from the candidate profile provided below. "
            "NEVER invent, guess, or assume any information not explicitly in the profile.\n\n"
            "Return ONLY a valid JSON object with:\n"
            "  answered: true if you can answer from the profile, false otherwise\n"
            "  answer: string answer, or null if answered=false\n"
            "  confidence: float 0.0-1.0\n"
            "  reason: string explanation if answered=false, else null\n\n"
            f"QUESTION: {question}\n"
            f"QUESTION TYPE: {question_type}"
            f"{options_section}\n\n"
            f"CANDIDATE PROFILE:\n{json.dumps(user_profile, default=str, indent=2)}"
        )

        data = self._call(prompt)
        return AnswerResult(
            answered=bool(data.get("answered", False)),
            answer=data.get("answer"),
            source="gemini",
            confidence=float(data.get("confidence", 0.85)),
            question_text=question,
            reason=data.get("reason"),
        )

    # ── Field extraction ───────────────────────────────────────────────────────

    def extract_job_fields(self, raw_text: str) -> Dict[str, Any]:
        """
        Extract structured fields from a raw job description text.
        Much more accurate than regex — Gemini handles messy JD formatting well.
        """
        prompt = (
            "Extract structured fields from this job description. "
            "Return ONLY a valid JSON object with exactly these fields:\n"
            "  required_skills: list of required skill strings\n"
            "  preferred_skills: list of nice-to-have skill strings\n"
            "  experience_min_years: integer or null\n"
            "  experience_max_years: integer or null\n"
            "  is_remote: boolean\n"
            "  is_hybrid: boolean\n"
            "  employment_type: one of 'full-time','part-time','contract','internship' or null\n\n"
            "Return ONLY valid JSON, no markdown.\n\n"
            f"JOB DESCRIPTION:\n{raw_text[:6000]}"
        )

        return self._call(prompt)

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _call(self, prompt: str) -> Dict[str, Any]:
        """Call Gemini and return parsed JSON. Returns {} on any failure."""
        import time
        if time.time() < self._rate_limited_until:
            return {}

        try:
            response = self._model.generate_content(prompt)
            text = response.text
            return self._parse_json(text)
        except Exception as exc:
            import logging
            str_exc = str(exc)
            if "429" in str_exc or "Quota" in str_exc or "ResourceExhausted" in str_exc or "TooManyRequests" in str_exc:
                self._rate_limited_until = time.time() + 300  # 5 min backoff
                logging.getLogger(__name__).warning(
                    "Gemini API quota/rate limit reached. Falling back to local provider for 5 mins."
                )
            else:
                logging.getLogger(__name__).error("Gemini API call failed: %s", exc)
            return {}

    @staticmethod
    def _parse_json(text: str) -> Dict[str, Any]:
        """Extract and parse the first JSON object from the response."""
        if not text:
            return {}
        # Strip markdown code fences if present
        text = re.sub(r"```(?:json)?\s*", "", text).strip()
        # Find first { ... }
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return {}
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            return {}
