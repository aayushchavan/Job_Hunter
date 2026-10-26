"""backend/app/schemas/user.py"""
from __future__ import annotations

import uuid
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    zip_code: Optional[str] = None
    current_title: Optional[str] = None
    current_company: Optional[str] = None
    years_of_experience: Optional[int] = None
    headline: Optional[str] = None
    summary: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    website_url: Optional[str] = None
    work_authorization: Optional[str] = None
    requires_sponsorship: Optional[bool] = None
    willing_to_relocate: Optional[bool] = None
    notice_period_days: Optional[int] = None
    desired_salary_min: Optional[int] = None
    desired_salary_max: Optional[int] = None
    salary_currency: Optional[str] = "INR"
    gender: Optional[str] = None
    disability_status: Optional[str] = None
    veteran_status: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(UserBase):
    email: Optional[EmailStr] = None  # type: ignore[assignment]
    password: Optional[str] = None


class UserRead(UserBase):
    id: uuid.UUID
    is_active: bool
    is_verified: bool

    model_config = {"from_attributes": True}


class UserProfile(UserRead):
    """Full profile returned for dashboard / form-filling context."""
    full_name: str

    model_config = {"from_attributes": True}
