import logging
import os
import re
import uuid
from pathlib import Path
from typing import List, Optional

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.resume import Resume
from app.models.user import User
from app.schemas.resume import ResumeCreate, ResumeRead, ResumeUpdate
from app.services.resume_service import resume_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resumes", tags=["Resumes"])

_ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


# ── GET /resumes ───────────────────────────────────────────────────────────────

@router.get("", response_model=List[ResumeRead])
async def list_resumes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ResumeRead]:
    """Return all active resumes for the current user."""
    result = await db.execute(
        select(Resume).where(
            Resume.user_id == current_user.id,
            Resume.is_active == True,
        )
    )
    resumes = result.scalars().all()
    return [ResumeRead.model_validate(r) for r in resumes]


# ── POST /resumes ──────────────────────────────────────────────────────────────

@router.post("", response_model=ResumeRead, status_code=status.HTTP_201_CREATED)
async def create_resume(
    payload: ResumeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResumeRead:
    """Create a resume record (without file — upload separately via /resumes/{id}/upload)."""
    # If this is flagged as default, clear existing defaults
    if payload.is_default:
        result = await db.execute(
            select(Resume).where(
                Resume.user_id == current_user.id,
                Resume.is_default == True,
            )
        )
        for existing in result.scalars().all():
            existing.is_default = False

    resume = Resume(
        user_id=current_user.id,
        name=payload.name,
        description=payload.description,
        is_default=payload.is_default,
        domain_tags=payload.domain_tags,
    )
    db.add(resume)
    await db.flush()
    return ResumeRead.model_validate(resume)


# ── POST /resumes/{id}/upload ─────────────────────────────────────────────────

@router.post("/{resume_id}/upload", response_model=ResumeRead)
async def upload_resume_file(
    resume_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResumeRead:
    """Upload a PDF/DOCX file and attach it to an existing resume record."""
    resume = await db.get(Resume, resume_id)
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    # Validate MIME type
    if file.content_type not in _ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file type: {file.content_type}. Use PDF or DOCX.",
        )

    # Validate size
    content = await file.read()
    if len(content) > settings.max_resume_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {settings.MAX_RESUME_SIZE_MB} MB.",
        )

    # Save file
    upload_dir = Path(settings.UPLOAD_DIR) / str(current_user.id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"{resume_id}_{file.filename}"

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    resume.file_path = str(file_path)
    resume.file_name = file.filename
    resume.file_size_bytes = len(content)
    resume.mime_type = file.content_type

    # Automatically extract text and rate resume
    try:
        await resume_service.parse_and_rate_resume(db, resume, current_user)
    except Exception as exc:
        logger.warning("Could not auto-analyze uploaded resume %s: %s", resume_id, exc)

    await db.flush()
    return ResumeRead.model_validate(resume)


# ── GET /resumes/{id} ─────────────────────────────────────────────────────────

@router.get("/{resume_id}", response_model=ResumeRead)
async def get_resume(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResumeRead:
    resume = await db.get(Resume, resume_id)
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    return ResumeRead.model_validate(resume)


# ── PUT /resumes/{id} ─────────────────────────────────────────────────────────

@router.put("/{resume_id}", response_model=ResumeRead)
async def update_resume(
    resume_id: uuid.UUID,
    payload: ResumeUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResumeRead:
    resume = await db.get(Resume, resume_id)
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    # If promoting to default, demote others
    if payload.is_default:
        result = await db.execute(
            select(Resume).where(
                Resume.user_id == current_user.id,
                Resume.is_default == True,
                Resume.id != resume_id,
            )
        )
        for other in result.scalars().all():
            other.is_default = False

    data = payload.model_dump(exclude_unset=True)
    data.pop("is_primary", None)
    for field, value in data.items():
        setattr(resume, field, value)

    await db.flush()
    return ResumeRead.model_validate(resume)


# ── DELETE /resumes/{id} ──────────────────────────────────────────────────────

@router.delete("/{resume_id}", status_code=status.HTTP_200_OK)
async def delete_resume(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    resume = await db.get(Resume, resume_id)
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    # Soft delete — keep the record so existing applications still reference it
    resume.is_active = False
    await db.flush()
    return {"deleted": True, "id": str(resume_id)}


# ── AI Rating, Matching & Auto-Pilot ───────────────────────────────────────────

@router.post("/{resume_id}/autofill")
async def autofill_profile_from_resume(
    resume_id: uuid.UUID,
    overwrite: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Extract profile information from the resume and autofill the user profile.
    Returns the updated profile fields and the application requirements checklist
    (clarifying which fields are required vs optional, and whether any required ones are missing).
    """
    resume = await db.get(Resume, resume_id)
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    result = await resume_service.autofill_user_profile(
        db, current_user, resume, overwrite=overwrite
    )
    await db.commit()
    return result


@router.get("/{resume_id}/requirements")
async def get_resume_requirements_checklist(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Returns the full ATS application field checklist:
    specifying which fields are REQUIRED vs OPTIONAL, their status ('filled' vs 'missing'),
    and highlights any missing required fields.
    """
    resume = await db.get(Resume, resume_id)
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    extracted = {}
    if resume.parsed_text:
        extracted = resume_service.extract_profile_details(resume.parsed_text)

    checklist = resume_service.get_requirements_checklist(current_user, extracted)
    return {
        "resume_id": str(resume.id),
        "years_of_experience": current_user.years_of_experience,
        "checklist": checklist,
    }


@router.post("/{resume_id}/analyze", response_model=ResumeRead)
async def analyze_resume(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResumeRead:
    """Extract text from resume, analyze skills, and rate with AI."""
    resume = await db.get(Resume, resume_id)
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    resume = await resume_service.parse_and_rate_resume(db, resume, current_user)
    await db.commit()
    return ResumeRead.model_validate(resume)


@router.post("/{resume_id}/find-jobs")
async def find_jobs_for_resume(
    resume_id: uuid.UUID,
    limit: int = 15,
    experience_years: Optional[int] = None,
    location: Optional[str] = Query(None, description="Target city, country, or 'Remote'"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Find and score matching jobs from sources based on resume skills, target roles, experience criteria, and location."""
    resume = await db.get(Resume, resume_id)
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    jobs = await resume_service.find_matching_jobs(
        db, current_user, resume, experience_years=experience_years, location=location, limit=limit
    )
    return {
        "resume_id": str(resume.id),
        "experience_years_used": experience_years if experience_years is not None else current_user.years_of_experience,
        "location_used": location or current_user.city or "Any / Remote",
        "total_found": len(jobs),
        "jobs": jobs,
    }


@router.post("/{resume_id}/auto-apply")
async def auto_apply_for_resume(
    resume_id: uuid.UUID,
    min_score: int = 70,
    max_applications: int = 5,
    experience_years: Optional[int] = None,
    location: Optional[str] = Query(None, description="Target city, country, or 'Remote'"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Automatically apply to jobs matching the resume with match_score >= min_score."""
    resume = await db.get(Resume, resume_id)
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    apps = await resume_service.auto_apply_to_jobs(
        db,
        current_user,
        resume,
        experience_years=experience_years,
        location=location,
        min_score=min_score,
        max_applications=max_applications,
    )
    await db.commit()
    return {
        "resume_id": str(resume.id),
        "location_used": location or current_user.city or "Any / Remote",
        "applications_created": len(apps),
        "applications": apps,
    }


@router.post("/{resume_id}/auto-pilot")
async def auto_pilot_for_resume(
    resume_id: uuid.UUID,
    experience_years: Optional[int] = None,
    location: Optional[str] = Query(None, description="Target city, country, or 'Remote'"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    1-Click Auto Pilot:
      1. Read & parse resume document
      2. Autofill user profile details & validate requirements checklist
      3. Rate & analyze with AI (score, ATS score, skills, roles)
      4. Find matching jobs with experience criteria and target location
      5. Auto-apply to qualifying jobs
    """
    try:
        result = await resume_service.run_auto_pilot(
            db, current_user, resume_id, experience_years=experience_years, location=location
        )
        await db.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.exception("Auto-pilot pipeline failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Auto-pilot failed: {str(exc)[:300]}"
        )


# ── GET /resumes/{id}/audit-report ─────────────────────────────────────────────

@router.get("/{resume_id}/audit-report")
async def get_resume_audit_report(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Return comprehensive ATS Resume Audit & Improvement Report for the given resume.
    Includes real ATS score breakdown, critical parser alerts, section reviews, and rewrites.
    """
    resume = await db.get(Resume, resume_id)
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    report = resume_service.generate_audit_report(resume, current_user)
    return report


# ── GET /resumes/{id}/audit-report/download ────────────────────────────────────

@router.get("/{resume_id}/audit-report/download")
async def download_resume_audit_report(
    resume_id: uuid.UUID,
    format: str = Query("markdown", description="Format: 'markdown' or 'text'"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Download the ATS Resume Audit & Improvement Report as a formatted markdown (.md) or text (.txt) file.
    """
    resume = await db.get(Resume, resume_id)
    if not resume or resume.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    report = resume_service.generate_audit_report(resume, current_user)
    md_content = report.get("markdown_report", "")

    clean_name = re.sub(r"[^\w\-_\.]", "_", resume.file_name or resume.name or "Resume")
    filename = f"{clean_name}_ATS_Audit_Report.md"
    media_type = "text/markdown; charset=utf-8"
    if format == "text":
        filename = f"{clean_name}_ATS_Audit_Report.txt"
        media_type = "text/plain; charset=utf-8"

    return Response(
        content=md_content.encode("utf-8"),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

