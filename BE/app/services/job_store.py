from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import Job


def create_dedupe_key(job: dict) -> str:
    apply_url = str(job.get("apply_url") or "").strip().lower().rstrip("/")
    if apply_url:
        return apply_url
    company = " ".join(str(job.get("company") or "").lower().split())
    title = " ".join(str(job.get("title") or "").lower().split())
    return f"{company}:{title}"


def upsert_jobs(
    db: Session,
    jobs: list[dict],
    source_key: str,
) -> tuple[int, set[str]]:
    now = datetime.now(timezone.utc)
    seen_keys = set()
    new_count = 0

    for job_data in jobs:
        source_job = dict(job_data)
        source_job["source"] = source_key
        dedupe_key = create_dedupe_key(source_job)
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)

        job = db.scalar(select(Job).where(Job.dedupe_key == dedupe_key))
        if job is None:
            job = Job(
                dedupe_key=dedupe_key,
                title=source_job.get("title", ""),
                company=source_job.get("company", ""),
                location=source_job.get("location", ""),
                description=source_job.get("description", ""),
                skills_mentioned=source_job.get("skills_mentioned", ""),
                posted_date=source_job.get("posted_date", ""),
                apply_url=source_job.get("apply_url", ""),
                source=source_key,
                first_seen_at=now,
                last_seen_at=now,
                is_active=True,
            )
            db.add(job)
            new_count += 1
        else:
            job.last_seen_at = now
            job.is_active = True

    db.flush()
    return new_count, seen_keys


def deactivate_missing_jobs(db: Session, source_key: str, seen_keys: set[str]) -> None:
    statement = update(Job).where(Job.source == source_key)
    if seen_keys:
        statement = statement.where(Job.dedupe_key.not_in(seen_keys))
    db.execute(statement.values(is_active=False))
