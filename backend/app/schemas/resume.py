"""backend/app/schemas/resume.py"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ResumeBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_default: bool = False
    is_primary: Optional[bool] = None
    domain_tags: Optional[List[str]] = None


class ResumeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_default: Optional[bool] = False
    is_primary: Optional[bool] = None
    domain_tags: Optional[List[str]] = None

    def model_post_init(self, __context) -> None:
        if self.is_primary is not None and not self.is_default:
            self.is_default = self.is_primary


class ResumeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_default: Optional[bool] = None
    is_primary: Optional[bool] = None
    domain_tags: Optional[List[str]] = None

    def model_post_init(self, __context) -> None:
        if self.is_primary is not None and self.is_default is None:
            self.is_default = self.is_primary


class ResumeRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: Optional[str] = None
    is_default: bool = False
    is_primary: bool = False
    domain_tags: Optional[List[str]] = None
    file_name: Optional[str] = None
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    is_active: bool
    score: Optional[int] = None
    extracted_skills: Optional[List[str]] = None
    extracted_roles: Optional[List[str]] = None
    rating_feedback: Optional[Dict[str, Any]] = None
    skills: Optional[List[str]] = None

    model_config = {"from_attributes": True}

    def model_post_init(self, __context) -> None:
        self.is_primary = self.is_default
        if not self.skills and self.extracted_skills:
            self.skills = self.extracted_skills

