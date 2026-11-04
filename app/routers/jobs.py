import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Job, JobMatch, ResumeProfile


router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
def list_jobs(
    location: str | None = None,
    role: str | None = None,
    min_overlap: float | None = Query(default=None, ge=0, le=100),
    company: str | None = None,
    q: str | None = None,
    is_active: bool | None = True,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort: str = Query(default="last_seen_at"),
    db: Session = Depends(get_db),
):
    sort_columns = {
        "last_seen_at": Job.last_seen_at,
        "first_seen_at": Job.first_seen_at,
        "company": Job.company,
        "title": Job.title,
    }
    if sort not in sort_columns:
        raise HTTPException(status_code=422, detail="Unsupported sort field.")

    statement = select(Job)
    profile = None
    if min_overlap is not None:
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
        statement = statement.join(
            JobMatch,
            (JobMatch.job_id == Job.id) & (JobMatch.profile_id == profile.id),
        ).where(
            JobMatch.skills_overlap.is_not(None),
            JobMatch.skills_overlap >= min_overlap,
        )
    if is_active is not None:
        statement = statement.where(Job.is_active == is_active)
    if location:
        statement = statement.where(Job.location.ilike(f"%{location}%"))
    if role:
        statement = statement.where(Job.title.ilike(f"%{role}%"))
    if company:
        statement = statement.where(Job.company.ilike(f"%{company}%"))
    if q:
        statement = statement.where(
            Job.title.ilike(f"%{q}%")
            | Job.company.ilike(f"%{q}%")
            | Job.description.ilike(f"%{q}%")
        )
    jobs = db.scalars(
        statement.order_by(sort_columns[sort].desc()).limit(limit).offset(offset)
    ).all()
    return [_job_response(job, db, profile) for job in jobs]


@router.get("/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return _job_response(job, db)


def _job_response(job: Job, db: Session, profile: ResumeProfile | None = None) -> dict:
    if profile is None:
        profile = db.scalar(
            select(ResumeProfile)
            .where(
                ResumeProfile.is_current.is_(True),
                ResumeProfile.approved.is_(True),
            )
            .order_by(ResumeProfile.created_at.desc())
        )
    match = None
    if profile is not None:
        match = db.scalar(
            select(JobMatch).where(
                JobMatch.job_id == job.id,
                JobMatch.profile_id == profile.id,
            )
        )
    return {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "description": job.description,
        "skills_mentioned": job.skills_mentioned,
        "posted_date": job.posted_date,
        "apply_url": job.apply_url,
        "source": job.source,
        "first_seen_at": job.first_seen_at,
        "last_seen_at": job.last_seen_at,
        "is_active": job.is_active,
        "skills_overlap": match.skills_overlap if match is not None else None,
        "matched_skills": json.loads(match.matched_skills) if match is not None else [],
        "missing_skills": json.loads(match.missing_skills) if match is not None else [],
    }
