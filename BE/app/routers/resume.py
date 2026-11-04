import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import ResumeProfile
from app.schemas import ResumeProfileEdit
from app.services.resume_parser import parse_and_store_resume
from app.services.resume_parsing import ResumeParseError


router = APIRouter(prefix="/resume", tags=["resume"])
PROFILE_LIST_FIELDS = (
    "skills",
    "skills_not_in_vocabulary",
    "projects",
    "education_lines",
    "degrees_detected",
    "experience_lines",
    "experience_date_ranges",
    "warnings",
)


def _profile_response(profile: ResumeProfile) -> dict:
    result = {
        "id": profile.id,
        "source_file": profile.source_file,
        "extraction_method": profile.extraction_method,
        "summary": profile.summary,
        "approved": profile.approved,
        "approved_at": profile.approved_at,
        "is_current": profile.is_current,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
    }
    for field in PROFILE_LIST_FIELDS:
        setattr_value = getattr(profile, field)
        result[field] = json.loads(setattr_value)
    return result


def _current_profile(db: Session) -> ResumeProfile:
    profile = db.scalar(
        select(ResumeProfile)
        .where(ResumeProfile.is_current.is_(True))
        .order_by(ResumeProfile.created_at.desc())
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="No current resume profile exists.")
    return profile


@router.post("/upload", status_code=201)
async def upload_resume(
    resume: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if resume.content_type != "application/pdf":
        raise HTTPException(status_code=415, detail="Upload a PDF with application/pdf content type.")
    filename = (resume.filename or "").lower()
    if not filename.endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Resume filename must have a .pdf extension.")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    content = await resume.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Resume exceeds the {settings.max_upload_mb} MB size limit.",
        )
    if not content:
        raise HTTPException(status_code=422, detail="The uploaded PDF is empty.")

    try:
        profile = parse_and_store_resume(db, content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ResumeParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _profile_response(profile)


@router.get("")
def get_resume(db: Session = Depends(get_db)):
    return _profile_response(_current_profile(db))


@router.patch("")
def edit_resume(body: ResumeProfileEdit, db: Session = Depends(get_db)):
    profile = _current_profile(db)
    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if value is not None:
            if field in PROFILE_LIST_FIELDS:
                setattr(profile, field, json.dumps(value, ensure_ascii=False))
            else:
                setattr(profile, field, value)
    profile.approved = False
    profile.approved_at = None
    profile.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(profile)
    return _profile_response(profile)


@router.post("/approve")
def approve_resume(db: Session = Depends(get_db)):
    profile = _current_profile(db)
    profile.approved = True
    profile.approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(profile)
    return _profile_response(profile)
