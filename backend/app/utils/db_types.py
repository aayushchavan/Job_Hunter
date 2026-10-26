"""
backend/app/utils/db_types.py

Custom SQLAlchemy types for cross-DB compatibility.

ArrayOfText:
  - PostgreSQL → native ARRAY(Text)
  - SQLite (test) → JSON

JsonBlob:
  - PostgreSQL → JSONB (indexable, efficient)
  - SQLite (test) → JSON

This allows the same ORM models to work with both PostgreSQL (production)
and SQLite in-memory (tests) without any monkey-patching.
"""
from __future__ import annotations

from typing import Any, List, Optional

from sqlalchemy import JSON, Text
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import TypeDecorator


class ArrayOfText(TypeDecorator):
    """
    A list-of-strings column:
     - PostgreSQL → native ARRAY(Text)
     - SQLite (tests) → JSON
    """
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_ARRAY(Text()))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value: Optional[List[str]], dialect: Dialect) -> Any:
        if dialect.name == "postgresql":
            return value
        return value  # JSON serializes lists natively

    def process_result_value(self, value: Any, dialect: Dialect) -> Optional[List[str]]:
        return value


class JsonBlob(TypeDecorator):
    """
    An arbitrary JSON/dict column:
     - PostgreSQL → JSONB (indexable, efficient)
     - SQLite (tests) → JSON
    """
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_JSONB())
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value: Any, dialect: Dialect) -> Any:
        return value

    def process_result_value(self, value: Any, dialect: Dialect) -> Any:
        return value
