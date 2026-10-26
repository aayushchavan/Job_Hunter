"""
backend/app/core/database.py
Async SQLAlchemy engine + session factory.
All DB interaction should use the `get_db` dependency.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# ── Async engine ──────────────────────────────────────────────────────────────
engine_kwargs: dict = {
    "echo": settings.DEBUG,
    "pool_pre_ping": True,
}

# Auto-detect Supabase or PgBouncer/Supavisor poolers (e.g. port 6543 or supabase hostnames)
# Disables prepared statement caching in asyncpg to avoid "DuplicatePreparedStatementError"
is_supabase_or_pooler = any(
    token in settings.DATABASE_URL.lower()
    for token in ["supabase", "6543", "pooler", "pgbouncer"]
)
if is_supabase_or_pooler:
    engine_kwargs["connect_args"] = {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    }

if not settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

# ── Session factory ───────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ── Base declarative class ────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """All ORM models inherit from this."""
    pass


# ── FastAPI dependency ────────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
