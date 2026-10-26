"""backend/app/api/v1/endpoints/auth.py — Register, login, and profile endpoints."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.user import UserCreate, UserRead, UserUpdate, UserProfile

router = APIRouter(prefix="/auth", tags=["Auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency — decodes JWT and returns the authenticated User."""
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    user = await db.get(User, uuid.UUID(user_id))
    if user is None or not user.is_active:
        raise credentials_exc
    return user


# ── POST /auth/register ────────────────────────────────────────────────────────

@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    """Create a new user account."""
    existing = await _get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.phone,
        city=payload.city,
        state=payload.state,
        country=payload.country,
        zip_code=payload.zip_code,
        current_title=payload.current_title,
        current_company=payload.current_company,
        years_of_experience=payload.years_of_experience,
        headline=payload.headline,
        summary=payload.summary,
        linkedin_url=payload.linkedin_url,
        github_url=payload.github_url,
        portfolio_url=payload.portfolio_url,
        website_url=payload.website_url,
        work_authorization=payload.work_authorization,
        requires_sponsorship=payload.requires_sponsorship,
        willing_to_relocate=payload.willing_to_relocate,
        notice_period_days=payload.notice_period_days,
        desired_salary_min=payload.desired_salary_min,
        desired_salary_max=payload.desired_salary_max,
        salary_currency=payload.salary_currency,
        gender=payload.gender,
        disability_status=payload.disability_status,
        veteran_status=payload.veteran_status,
    )
    db.add(user)
    await db.flush()
    return UserRead.model_validate(user)


# ── POST /auth/login ───────────────────────────────────────────────────────────

@router.post("/login")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Authenticate and return access + refresh tokens."""
    user = await _get_user_by_email(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled.",
        )

    return {
        "access_token": create_access_token(str(user.id)),
        "refresh_token": create_refresh_token(str(user.id)),
        "token_type": "bearer",
    }


# ── GET /auth/me ───────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserProfile)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserProfile:
    """Return the currently authenticated user's full profile."""
    return UserProfile(
        **UserRead.model_validate(current_user).model_dump(),
        full_name=current_user.full_name,
    )


# ── PUT /auth/me ───────────────────────────────────────────────────────────────

@router.put("/me", response_model=UserProfile)
async def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfile:
    """Update the authenticated user's profile."""
    update_data = payload.model_dump(exclude_unset=True)

    # Handle password change separately
    if "password" in update_data:
        raw_pw = update_data.pop("password")
        if raw_pw:
            current_user.hashed_password = hash_password(raw_pw)

    for field, value in update_data.items():
        if hasattr(current_user, field):
            setattr(current_user, field, value)

    await db.flush()
    return UserProfile(
        **UserRead.model_validate(current_user).model_dump(),
        full_name=current_user.full_name,
    )
