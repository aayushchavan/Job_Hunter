"""
backend/app/core/config.py
Central application configuration using pydantic-settings.
All values are loaded from environment variables / .env file.

AI_PROVIDER controls which AI backend is used:
  "local"  — deterministic Python logic only, no external AI API (DEFAULT)
  "claude" — Anthropic Claude API (requires ANTHROPIC_API_KEY)

The application starts and runs fully without an Anthropic API key
when AI_PROVIDER=local.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# config.py lives at: backend/app/core/config.py
# .env lives at:      Job-apply-bot/.env  (one level above backend/)
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent   # → backend/
_PROJECT_ROOT = _BACKEND_DIR.parent                             # → Job-apply-bot/
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    APP_NAME: str = "AI Job Hunter"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "dev-secret-key-change-in-production-32ch"
    ENCRYPTION_KEY: str = "dev-encryption-key-change-production32"

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str
    DATABASE_URL_SYNC: str

    # ── AI Provider ───────────────────────────────────────────────────────────
    # "local"  → no external AI calls, fully deterministic (default)
    # "gemini" → Google Gemini API (GEMINI_API_KEY must be set, free tier available)
    # "claude" → Anthropic Claude API (ANTHROPIC_API_KEY must be set)
    AI_PROVIDER: Literal["local", "claude", "gemini"] = "local"

    # Anthropic / Claude — OPTIONAL. Only required when AI_PROVIDER=claude.
    ANTHROPIC_API_KEY: Optional[str] = None
    CLAUDE_MODEL: str = "claude-3-5-sonnet-20241022"
    CLAUDE_MAX_TOKENS: int = 4096

    # Google Gemini — OPTIONAL. Only required when AI_PROVIDER=gemini.
    # Get key at: https://aistudio.google.com/app/apikey
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.5-flash"

    # ── JWT ───────────────────────────────────────────────────────────────────
    JWT_SECRET: str = "dev-jwt-secret-change-in-production-32chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # 30 days
    REFRESH_TOKEN_EXPIRE_DAYS: int = 90       # 90 days

    # ── Job Discovery APIs (all optional) ─────────────────────────────────────
    ADZUNA_APP_ID: Optional[str] = None
    ADZUNA_APP_KEY: Optional[str] = None
    ADZUNA_COUNTRY: str = "in"           # in=India, gb=UK, us=US, etc.

    GREENHOUSE_API_KEY: Optional[str] = None
    GREENHOUSE_ON_BEHALF_OF: Optional[str] = None

    LEVER_API_KEY: Optional[str] = None

    # ── Auto-Apply ────────────────────────────────────────────────────────────
    AUTO_APPLY_ENABLED: bool = False
    AUTO_APPLY_MODE: str = "safe"          # "safe" | "auto"
    AUTO_APPLY_THRESHOLD: int = 90         # minimum match score 0–100
    AUTO_APPLY_MAX_PER_DAY: int = 10
    AUTO_APPLY_DELAY_MIN_SEC: int = 30
    AUTO_APPLY_DELAY_MAX_SEC: int = 120
    AUTO_APPLY_MAX_RETRIES: int = 3
    AUTO_APPLY_TEST_MODE: bool = True      # when True: NEVER clicks Submit

    # ── Playwright ────────────────────────────────────────────────────────────
    PLAYWRIGHT_HEADLESS: bool = True
    PLAYWRIGHT_BROWSER_PROFILE_PATH: str = "./browser_profile"
    PLAYWRIGHT_TIMEOUT_MS: int = 30000

    # ── File Storage ──────────────────────────────────────────────────────────
    UPLOAD_DIR: str = "./uploads"
    MAX_RESUME_SIZE_MB: int = 5

    # ── CORS ──────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # ── Validators ────────────────────────────────────────────────────────────

    @model_validator(mode="after")
    def _validate_claude_config(self) -> "Settings":
        """
        If AI_PROVIDER=claude the API key must be non-empty.
        Raises a clear ValueError so the user knows exactly what to fix.
        """
        if self.AI_PROVIDER == "claude":
            if not self.ANTHROPIC_API_KEY or not self.ANTHROPIC_API_KEY.strip():
                raise ValueError(
                    "AI_PROVIDER=claude requires ANTHROPIC_API_KEY to be set. "
                    "Either set the key or switch to AI_PROVIDER=local."
                )
        return self

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_test_mode(self) -> bool:
        return self.AUTO_APPLY_TEST_MODE

    @property
    def max_resume_size_bytes(self) -> int:
        return self.MAX_RESUME_SIZE_MB * 1024 * 1024

    @property
    def uses_claude(self) -> bool:
        """True only when AI_PROVIDER=claude AND key is set."""
        return self.AI_PROVIDER == "claude" and bool(self.ANTHROPIC_API_KEY)

    @property
    def uses_local_ai(self) -> bool:
        return self.AI_PROVIDER == "local"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
