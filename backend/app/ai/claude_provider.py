"""
backend/app/ai/claude_provider.py

ClaudeAIProvider — Anthropic Claude-based implementation of AIProvider.

THIS MODULE IS NEVER IMPORTED when AI_PROVIDER=local.
The factory (factory.py) is the only code that imports this.

Requires:
  pip install anthropic
  AI_PROVIDER=claude
  ANTHROPIC_API_KEY=<your-key>
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.ai.base import AIProvider, AnswerResult, MatchResult


class ClaudeAIProvider(AIProvider):
    """
    AI provider backed by Anthropic Claude.
    Only instantiated when AI_PROVIDER=claude.
    """

    def __init__(self, api_key: str, model: str, max_tokens: int) -> None:
        # Import is intentionally deferred to this class —
        # never executed in local mode.
        try:
            import anthropic  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "The 'anthropic' package is not installed. "
                "Run: pip install anthropic"
            ) from exc

        import anthropic as _anthropic
        self._client = _anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    @property
    def provider_name(self) -> str:
        return "claude"

    def score_job_match(
        self,
        job: Dict[str, Any],
        user_profile: Dict[str, Any],
    ) -> MatchResult:
        prompt = (
            "You are a job-matching assistant. Given the job and candidate profile below, "
            "return a JSON object with fields: score (0-100), matched_skills (list), "
            "missing_skills (list), reasons (list of strings), "
            "breakdown (dict of dimension -> score).\n\n"
            f"Job: {json.dumps(job, indent=2)}\n\n"
            f"Profile: {json.dumps(user_profile, indent=2)}"
        )
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        # Extract JSON block
        data = self._extract_json(text)
        return MatchResult(
            score=int(data.get("score", 0)),
            matched_skills=data.get("matched_skills", []),
            missing_skills=data.get("missing_skills", []),
            reasons=data.get("reasons", []),
            breakdown=data.get("breakdown", {}),
        )

    def answer_question(
        self,
        question: str,
        question_type: str,
        options: Optional[List[str]],
        user_profile: Dict[str, Any],
    ) -> AnswerResult:
        options_text = f"\nOptions: {options}" if options else ""
        prompt = (
            "You are filling out a job application. Answer ONLY from the candidate "
            "profile provided. If the question cannot be answered from the profile, "
            "return {\"answered\": false, \"reason\": \"...\"}. "
            "NEVER invent information. "
            "Return JSON: {\"answered\": bool, \"answer\": str|null, \"confidence\": 0-1, \"reason\": str|null}\n\n"
            f"Question: {question}{options_text}\n\n"
            f"Profile: {json.dumps(user_profile, indent=2)}"
        )
        response = self._client.messages.create(
            model=self._model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        data = self._extract_json(response.content[0].text)
        return AnswerResult(
            answered=bool(data.get("answered", False)),
            answer=data.get("answer"),
            source="claude",
            confidence=float(data.get("confidence", 0.8)),
            question_text=question,
            reason=data.get("reason"),
        )

    def extract_job_fields(self, raw_text: str) -> Dict[str, Any]:
        prompt = (
            "Extract structured fields from this job description. "
            "Return JSON with: required_skills (list), preferred_skills (list), "
            "experience_min_years (int|null), experience_max_years (int|null), "
            "is_remote (bool), is_hybrid (bool), employment_type (str|null).\n\n"
            f"Job description:\n{raw_text[:4000]}"
        )
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return self._extract_json(response.content[0].text)

    @staticmethod
    def _extract_json(text: str) -> Dict[str, Any]:
        """Extract first JSON object from a text response."""
        import re
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return {}
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            return {}
