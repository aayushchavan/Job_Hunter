"""backend/app/models/eligibility.py"""
from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin, UUIDType
from app.utils.db_types import ArrayOfText


class EligibilityCriteria(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Hard-stop eligibility rules. If ANY criterion fails → REJECTED.
    Checked BEFORE match scoring to avoid unnecessary Claude API calls.
    """

    __tablename__ = "eligibility_criteria"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    # Role / Title
    allowed_roles: Mapped[Optional[List[str]]] = mapped_column(ArrayOfText())
    excluded_roles: Mapped[Optional[List[str]]] = mapped_column(ArrayOfText())

    # Experience
    max_experience_years: Mapped[Optional[int]] = mapped_column(Integer)

    # Education
    min_education: Mapped[Optional[str]] = mapped_column(String(100))
    graduation_year: Mapped[Optional[int]] = mapped_column(Integer)

    # Domain
    allowed_domains: Mapped[Optional[List[str]]] = mapped_column(ArrayOfText())
    excluded_domains: Mapped[Optional[List[str]]] = mapped_column(ArrayOfText())

    # Location
    allowed_locations: Mapped[Optional[List[str]]] = mapped_column(ArrayOfText())
    allow_remote: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Salary
    min_salary: Mapped[Optional[int]] = mapped_column(Integer)
    salary_currency: Mapped[Optional[str]] = mapped_column(String(10), default="INR")

    # Employment type
    allowed_employment_types: Mapped[Optional[List[str]]] = mapped_column(ArrayOfText())

    # Company exclusions
    excluded_companies: Mapped[Optional[List[str]]] = mapped_column(ArrayOfText())

    # Required skills (positive filter — user MUST have these)
    required_skills: Mapped[Optional[List[str]]] = mapped_column(ArrayOfText())

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
