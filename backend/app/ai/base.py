"""
backend/app/ai/base.py

Abstract AI provider interface.

All AI operations in the system go through this interface.
The concrete implementation is determined by AI_PROVIDER in config.

When AI_PROVIDER=local: uses LocalAIProvider (pure Python, no external calls)
When AI_PROVIDER=claude: uses ClaudeAIProvider (Anthropic API)

Rules:
- LocalAIProvider must NEVER import anthropic.
- ClaudeAIProvider must NOT be imported when AI_PROVIDER=local.
- No code outside this package may call anthropic directly.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MatchResult:
    """
    Result of scoring a job against a user profile.
    Returned by AIProvider.score_job_match().
    """
    score: int                          # 0–100, deterministic
    matched_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)
    breakdown: Dict[str, int] = field(default_factory=dict)
    # e.g. {"role": 18, "experience": 20, "skills": 22, ...}


@dataclass
class AnswerResult:
    """
    Result of attempting to answer a single application question.
    Returned by AIProvider.answer_question().
    """
    answered: bool                      # False means USER_INPUT_REQUIRED
    answer: Optional[str] = None
    source: str = "local"               # "local" | "claude" | "user_input"
    confidence: float = 1.0             # 0.0–1.0
    question_text: str = ""
    reason: Optional[str] = None        # why it couldn't be answered (if !answered)


class AIProvider(ABC):
    """
    Abstract base for all AI providers.

    Implement this to add a new AI backend.
    Currently implemented:
      LocalAIProvider  — deterministic Python (AI_PROVIDER=local)
      ClaudeAIProvider — Anthropic Claude (AI_PROVIDER=claude)
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name, e.g. "local" or "claude"."""

    @abstractmethod
    def score_job_match(
        self,
        job: Dict[str, Any],
        user_profile: Dict[str, Any],
    ) -> MatchResult:
        """
        Score a job against the user profile.
        Must return a deterministic MatchResult with score 0–100.
        Must NOT make network calls in local mode.
        """

    @abstractmethod
    def answer_question(
        self,
        question: str,
        question_type: str,
        options: Optional[List[str]],
        user_profile: Dict[str, Any],
    ) -> AnswerResult:
        """
        Answer a single application form question from the user's profile.
        If the question cannot be answered safely, return AnswerResult(answered=False).
        Must NEVER invent information.
        """

    @abstractmethod
    def extract_job_fields(self, raw_text: str) -> Dict[str, Any]:
        """
        Extract structured job fields (title, skills, experience, etc.)
        from raw job description text.
        In local mode: uses regex + keyword matching.
        In Claude mode: calls the API.
        """
