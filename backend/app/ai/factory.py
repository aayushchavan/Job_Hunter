"""
backend/app/ai/factory.py

AI provider factory.

Usage:
    from app.ai.factory import get_ai_provider
    ai = get_ai_provider()
    result = ai.score_job_match(job, profile)

The provider is selected from settings.AI_PROVIDER:
  "local"  → LocalAIProvider  (no external calls, default, always free)
  "gemini" → GeminiAIProvider (Google Gemini API, free tier: 1500 req/day)
  "claude" → ClaudeAIProvider (Anthropic Claude API, paid)

Each provider is imported only when selected — other providers
are never imported and their packages don't need to be installed.
"""
from __future__ import annotations

from functools import lru_cache

from app.ai.base import AIProvider
from app.core.config import settings


@lru_cache(maxsize=1)
def get_ai_provider() -> AIProvider:
    """
    Return the singleton AI provider configured by AI_PROVIDER.

    Calling this repeatedly returns the same cached instance.
    Call get_ai_provider.cache_clear() in tests to reset.
    """
    if settings.AI_PROVIDER == "local":
        from app.ai.local_provider import LocalAIProvider
        return LocalAIProvider()

    if settings.AI_PROVIDER == "gemini":
        if not settings.GEMINI_API_KEY or not settings.GEMINI_API_KEY.strip():
            raise ValueError(
                "AI_PROVIDER=gemini requires GEMINI_API_KEY in your .env file. "
                "Get a free key at: https://aistudio.google.com/app/apikey\n"
                "Or switch AI_PROVIDER=local to use the free local provider."
            )
        from app.ai.gemini_provider import GeminiAIProvider
        return GeminiAIProvider(
            api_key=settings.GEMINI_API_KEY,
            model=settings.GEMINI_MODEL,
        )

    if settings.AI_PROVIDER == "claude":
        if not settings.ANTHROPIC_API_KEY or not settings.ANTHROPIC_API_KEY.strip():
            raise ValueError(
                "AI_PROVIDER=claude requires ANTHROPIC_API_KEY. "
                "Set it in .env or switch AI_PROVIDER=local."
            )
        from app.ai.claude_provider import ClaudeAIProvider
        return ClaudeAIProvider(
            api_key=settings.ANTHROPIC_API_KEY,
            model=settings.CLAUDE_MODEL,
            max_tokens=settings.CLAUDE_MAX_TOKENS,
        )

    raise ValueError(
        f"Unknown AI_PROVIDER: '{settings.AI_PROVIDER}'. "
        "Valid values: 'local', 'gemini', 'claude'."
    )

