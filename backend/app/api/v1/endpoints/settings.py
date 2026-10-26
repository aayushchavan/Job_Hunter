"""backend/app/api/v1/endpoints/settings.py — Auto-apply settings endpoint."""
from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.application import AutoApplySettingsRead, AutoApplySettingsUpdate
from app.services.application_service import application_service

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("/auto-apply", response_model=AutoApplySettingsRead)
async def get_auto_apply_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AutoApplySettingsRead:
    s = await application_service.get_or_create_settings(db, current_user.id)
    return AutoApplySettingsRead.model_validate(s)


@router.put("/auto-apply", response_model=AutoApplySettingsRead)
async def update_auto_apply_settings(
    payload: AutoApplySettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AutoApplySettingsRead:
    s = await application_service.update_settings(db, current_user.id, payload)
    return AutoApplySettingsRead.model_validate(s)

