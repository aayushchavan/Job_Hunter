"""backend/app/models/user.py"""
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.resume import Resume
    from app.models.application import Application, AutoApplySettings


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """User account + full candidate profile used by the application engine."""

    __tablename__ = "users"

    # ── Auth ──────────────────────────────────────────────────────────────────
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Personal ──────────────────────────────────────────────────────────────
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    phone: Mapped[Optional[str]] = mapped_column(String(30))

    # ── Location ──────────────────────────────────────────────────────────────
    city: Mapped[Optional[str]] = mapped_column(String(100))
    state: Mapped[Optional[str]] = mapped_column(String(100))
    country: Mapped[Optional[str]] = mapped_column(String(100))
    zip_code: Mapped[Optional[str]] = mapped_column(String(20))

    # ── Professional ──────────────────────────────────────────────────────────
    current_title: Mapped[Optional[str]] = mapped_column(String(150))
    current_company: Mapped[Optional[str]] = mapped_column(String(150))
    years_of_experience: Mapped[Optional[int]] = mapped_column(Integer)
    headline: Mapped[Optional[str]] = mapped_column(String(255))
    summary: Mapped[Optional[str]] = mapped_column(Text)

    # ── Links ─────────────────────────────────────────────────────────────────
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500))
    github_url: Mapped[Optional[str]] = mapped_column(String(500))
    portfolio_url: Mapped[Optional[str]] = mapped_column(String(500))
    website_url: Mapped[Optional[str]] = mapped_column(String(500))

    # ── Work Authorization (NEVER fabricated) ─────────────────────────────────
    work_authorization: Mapped[Optional[str]] = mapped_column(String(100))
    requires_sponsorship: Mapped[Optional[bool]] = mapped_column(Boolean)
    willing_to_relocate: Mapped[Optional[bool]] = mapped_column(Boolean)
    notice_period_days: Mapped[Optional[int]] = mapped_column(Integer)

    # ── Desired Salary ────────────────────────────────────────────────────────
    desired_salary_min: Mapped[Optional[int]] = mapped_column(Integer)
    desired_salary_max: Mapped[Optional[int]] = mapped_column(Integer)
    salary_currency: Mapped[Optional[str]] = mapped_column(String(10), default="INR")

    # ── Sensitive / EEO (user-controlled, NEVER fabricated) ───────────────────
    gender: Mapped[Optional[str]] = mapped_column(String(50))
    disability_status: Mapped[Optional[str]] = mapped_column(String(100))
    veteran_status: Mapped[Optional[str]] = mapped_column(String(100))

    # ── Relationships ─────────────────────────────────────────────────────────
    resumes: Mapped[List["Resume"]] = relationship(
        "Resume", back_populates="user", cascade="all, delete-orphan"
    )
    applications: Mapped[List["Application"]] = relationship(
        "Application", back_populates="user", cascade="all, delete-orphan"
    )
    auto_apply_settings: Mapped[Optional["AutoApplySettings"]] = relationship(
        "AutoApplySettings", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def full_name(self) -> str:
        parts = [self.first_name, self.last_name]
        return " ".join(p for p in parts if p) or self.email
