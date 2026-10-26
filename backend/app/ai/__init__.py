"""
backend/app/ai/__init__.py

Public interface for the AI provider package.

Import from here:
    from app.ai import get_ai_provider, AIProvider, MatchResult, AnswerResult
"""
from app.ai.base import AIProvider, AnswerResult, MatchResult
from app.ai.factory import get_ai_provider

__all__ = ["AIProvider", "AnswerResult", "MatchResult", "get_ai_provider"]
