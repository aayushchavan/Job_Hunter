"""backend/app/models/resume.py"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin, UUIDType
from app.utils.db_types import ArrayOfText

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.application import Application


class Resume(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single resume document.
    Users can hold multiple resumes tagged by domain (backend, ai/ml, fullstack…).
    The resume selection engine uses domain_tags to pick the best match.
    """

    __tablename__ = "resumes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Domain tags used by the resume selection engine
    domain_tags: Mapped[Optional[List[str]]] = mapped_column(ArrayOfText())

    # File storage
    file_path: Mapped[Optional[str]] = mapped_column(String(500))
    file_name: Mapped[Optional[str]] = mapped_column(String(255))
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100))

    # Parsed text for AI analysis and question answering
    parsed_text: Mapped[Optional[str]] = mapped_column(Text)

    # AI Analysis & Rating
    score: Mapped[Optional[int]] = mapped_column(Integer)
    extracted_skills: Mapped[Optional[List[str]]] = mapped_column(ArrayOfText())
    extracted_roles: Mapped[Optional[List[str]]] = mapped_column(ArrayOfText())
    rating_feedback: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)

    user: Mapped["User"] = relationship("User", back_populates="resumes")
    applications: Mapped[List["Application"]] = relationship(
        "Application", back_populates="resume"
    )
