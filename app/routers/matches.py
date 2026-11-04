import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Job, JobMatch, ResumeProfile
from app.services.matching import match_job_to_profile, recompute_active_matches


router = APIRouter(tags=["matches"])


@router.post("/matches/recompute")
def recompute_matches(db: Session = Depends(get_db)):
    profile, count = recompute_active_matches(db)
    if profile is None:
        raise HTTPException(
            status_code=409,
            detail="An approved current resume profile is required for matching.",
        )
    return {
        "profile_id": profile.id,
        "computed_jobs": count,
        "label": "Skills overlap",
        "note": "Skills overlap is not a hiring probability.",
    }


@router.get("/jobs/{job_id}/match")
def get_job_match(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    profile = db.scalar(
        select(ResumeProfile)
        .where(
            ResumeProfile.is_current.is_(True),
            ResumeProfile.approved.is_(True),
        )
        .order_by(ResumeProfile.created_at.desc())
    )
    if profile is None:
        raise HTTPException(
            status_code=409,
            detail="An approved current resume profile is required for matching.",
        )

    match = db.scalar(
        select(JobMatch).where(
            JobMatch.job_id == job_id,
            JobMatch.profile_id == profile.id,
        )
    )
    if match is None:
        match = match_job_to_profile(db, job, profile)
        db.commit()
        db.refresh(match)
    return {
        "job_id": job_id,
        "profile_id": profile.id,
        "skills_overlap": match.skills_overlap,
        "matched_skills": json.loads(match.matched_skills),
        "missing_skills": json.loads(match.missing_skills),
        "label": "Skills overlap",
        "note": "Skills overlap is not a hiring probability.",
    }
