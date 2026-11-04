import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import load_search_config
from app.models import Job, JobMatch, ResumeProfile
from app.services.skills import canonical_skill, extract_canonical_skills


def calculate_skills_overlap(
    job_skills: list[str],
    profile_skills: list[str],
    vocabulary: list[str] | None = None,
) -> tuple[float | None, list[str], list[str]]:
    job_canonical = list(
        dict.fromkeys(
            canonical
            for skill in job_skills
            if (canonical := canonical_skill(skill, vocabulary)) is not None
        )
    )
    profile_canonical = {
        canonical
        for skill in profile_skills
        if (canonical := canonical_skill(skill, vocabulary)) is not None
    }

    if not job_canonical:
        return None, [], []

    matched = [skill for skill in job_canonical if skill in profile_canonical]
    missing = [skill for skill in job_canonical if skill not in profile_canonical]
    overlap = round(len(matched) / len(job_canonical) * 100, 1)
    return overlap, matched, missing


def match_job_to_profile(
    db: Session,
    job: Job,
    profile: ResumeProfile,
    vocabulary: list[str] | None = None,
) -> JobMatch:
    if vocabulary is None:
        vocabulary = load_search_config().get("skills", [])
    job_skills = extract_canonical_skills(job.description, vocabulary)
    profile_skills = json.loads(profile.skills)
    overlap, matched, missing = calculate_skills_overlap(
        job_skills, profile_skills, vocabulary
    )

    match = db.scalar(
        select(JobMatch).where(
            JobMatch.job_id == job.id,
            JobMatch.profile_id == profile.id,
        )
    )
    if match is None:
        match = JobMatch(job_id=job.id, profile_id=profile.id)
        db.add(match)

    match.skills_overlap = overlap
    match.matched_skills = json.dumps(matched)
    match.missing_skills = json.dumps(missing)
    match.computed_at = datetime.now(timezone.utc)
    db.flush()
    return match


def recompute_active_matches(db: Session) -> tuple[ResumeProfile | None, int]:
    profile = db.scalar(
        select(ResumeProfile)
        .where(
            ResumeProfile.is_current.is_(True),
            ResumeProfile.approved.is_(True),
        )
        .order_by(ResumeProfile.created_at.desc())
    )
    if profile is None:
        return None, 0

    jobs = db.scalars(select(Job).where(Job.is_active.is_(True))).all()
    vocabulary = load_search_config().get("skills", [])
    for job in jobs:
        match_job_to_profile(db, job, profile, vocabulary)
    db.commit()
    return profile, len(jobs)
