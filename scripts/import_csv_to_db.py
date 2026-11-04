import argparse
import csv
import os
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import ROOT_DIR
from app.database import DATABASE_URL, SessionLocal
from app.models import Application, Job
from app.services.applications import create_imported_application
from app.services.job_store import create_dedupe_key, upsert_jobs


LEGACY_STATUS_MAP = {
    "needs verification": "Interested",
    "ready to apply": "Application Prepared",
    "rejected": "Rejected",
}
LEGACY_NOTE_FIELDS = (
    "india_eligibility",
    "fresher_eligibility",
    "eligibility_notes",
    "experience_requirement",
    "application_date",
    "follow_up_date",
)
JOB_REQUIRED_FIELDS = ("title", "company", "url")
JOB_SOURCE = "legacy_csv"


@dataclass
class ImportSummary:
    jobs_rows: int = 0
    jobs_created: int = 0
    jobs_existing: int = 0
    application_rows: int = 0
    applications_created: int = 0
    applications_existing: int = 0
    not_reviewed_without_history: int = 0
    applied_downgraded: int = 0
    skipped_jobs: Counter = field(default_factory=Counter)
    skipped_applications: Counter = field(default_factory=Counter)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {path.name}")
        return [
            {key: value or "" for key, value in row.items() if key is not None}
            for row in reader
        ]


def _job_data(row: dict[str, str]) -> tuple[dict | None, str | None]:
    missing = [
        key
        for key in JOB_REQUIRED_FIELDS
        if not (row.get(key) or "").strip()
    ]
    if missing:
        return None, f"missing_{'_'.join(missing)}"

    source = (row.get("source") or "").strip() or JOB_SOURCE
    job = {
        "title": row["title"],
        "company": row["company"],
        "location": row.get("location", ""),
        "url": row["url"],
        "apply_url": row["url"],
        "description": row.get("description", ""),
        "source": source,
        "skills_mentioned": row.get("skills_mentioned", ""),
        "posted_date": row.get("posted_date", ""),
    }
    return job, None


def _store_job(db: Session, row: dict[str, str], summary: ImportSummary) -> Job | None:
    job_data, reason = _job_data(row)
    if reason:
        summary.skipped_jobs[reason] += 1
        return None

    dedupe_key = create_dedupe_key(job_data)
    existing = db.scalar(select(Job).where(Job.dedupe_key == dedupe_key))
    if existing is not None:
        summary.jobs_existing += 1
        return existing

    upsert_jobs(db, [job_data], job_data["source"])
    job = db.scalar(select(Job).where(Job.dedupe_key == dedupe_key))
    if job is None:
        raise RuntimeError("Job store did not persist an imported job.")
    summary.jobs_created += 1
    return job


def _legacy_notes(row: dict[str, str]) -> str:
    lines = []
    included = set()
    for key in LEGACY_NOTE_FIELDS:
        value = (row.get(key) or "").strip()
        if value:
            lines.append(f"legacy {key}: {value}")
            included.add(key)

    for key, raw_value in row.items():
        if "eligibility" not in key.lower() or key in included:
            continue
        value = (raw_value or "").strip()
        if value:
            lines.append(f"legacy {key}: {value}")

    status = (row.get("application_status") or "").strip()
    if status.casefold() == "needs verification":
        lines.append("legacy status: Needs Verification")
    return "\n".join(lines)


def _has_review_history(row: dict[str, str]) -> bool:
    if any(
        (row.get(key) or "").strip()
        for key in ("application_date", "follow_up_date", "eligibility_notes")
    ):
        return True
    return any(
        "eligibility" in key.lower() and (value or "").strip()
        for key, value in row.items()
    )


def _application_status(row: dict[str, str], confirm_legacy_applied: bool):
    status = (row.get("application_status") or "").strip()
    normalized = status.casefold()

    if normalized == "not reviewed":
        if _has_review_history(row):
            return "Interested", False
        return None, False
    if normalized == "applied":
        if confirm_legacy_applied:
            return "Applied", True
        return "Application Prepared", False
    return LEGACY_STATUS_MAP.get(normalized), False


def _import_rows(
    db: Session,
    jobs_path: Path,
    applications_path: Path,
    confirm_legacy_applied: bool,
) -> ImportSummary:
    summary = ImportSummary()
    jobs_rows = _read_csv(jobs_path)
    summary.jobs_rows = len(jobs_rows)
    for row in jobs_rows:
        _store_job(db, row, summary)

    application_rows = _read_csv(applications_path)
    summary.application_rows = len(application_rows)
    for row in application_rows:
        status_value = (row.get("application_status") or "").strip()
        target_status, confirmed = _application_status(
            row,
            confirm_legacy_applied,
        )
        not_reviewed_without_history = (
            status_value.casefold() == "not reviewed"
            and target_status is None
        )
        if target_status is None and not not_reviewed_without_history:
            reason = "empty_status" if not status_value else "unsupported_status"
            summary.skipped_applications[reason] += 1
            continue

        job_data, reason = _job_data(row)
        if reason:
            summary.skipped_applications[reason] += 1
            continue

        dedupe_key = create_dedupe_key(job_data)
        job = db.scalar(select(Job).where(Job.dedupe_key == dedupe_key))
        if job is None:
            job = _store_job(db, row, summary)
        if job is None:
            continue

        if not_reviewed_without_history:
            summary.not_reviewed_without_history += 1
            continue

        existing = db.scalar(
            select(Application).where(Application.job_id == job.id)
        )
        if existing is not None:
            summary.applications_existing += 1
            continue

        create_imported_application(
            db,
            job_id=job.id,
            status=target_status,
            notes=_legacy_notes(row),
            confirmed_by_user=confirmed,
        )
        summary.applications_created += 1
        if status_value.casefold() == "applied" and target_status == "Application Prepared":
            summary.applied_downgraded += 1

    return summary


def import_csv_rows(
    db: Session,
    jobs_path: Path,
    applications_path: Path,
    *,
    dry_run: bool = False,
    confirm_legacy_applied: bool = False,
) -> ImportSummary:
    transaction = db.begin()
    try:
        summary = _import_rows(
            db,
            jobs_path,
            applications_path,
            confirm_legacy_applied,
        )
    except Exception:
        transaction.rollback()
        raise
    if dry_run:
        transaction.rollback()
    else:
        transaction.commit()
    return summary


def _database_file() -> Path:
    if DATABASE_URL.get_backend_name() != "sqlite":
        raise ValueError("CSV import backup requires a SQLite database.")
    database = DATABASE_URL.database
    if not database or database == ":memory:" or database.startswith("file:"):
        raise ValueError("CSV import requires a file-backed SQLite database.")
    return Path(database).resolve()


def create_database_backup(now: datetime | None = None) -> Path:
    source_path = _database_file()
    if not source_path.is_file():
        raise FileNotFoundError(
            "Database file does not exist; initialize the database before importing."
        )

    backup_dir = ROOT_DIR / "data"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    backup_path = backup_dir / f"backup-{timestamp}.db"

    descriptor = os.open(
        backup_path,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY,
        0o600,
    )
    os.close(descriptor)
    try:
        with sqlite3.connect(source_path) as source, sqlite3.connect(
            backup_path
        ) as backup:
            source.backup(backup)
    except Exception:
        backup_path.unlink(missing_ok=True)
        raise
    return backup_path


def print_summary(summary: ImportSummary, output: TextIO) -> None:
    print(f"Jobs CSV rows: {summary.jobs_rows}", file=output)
    print(f"Jobs created: {summary.jobs_created}", file=output)
    print(f"Jobs already present: {summary.jobs_existing}", file=output)
    print(f"Application CSV rows: {summary.application_rows}", file=output)
    print(f"Applications created: {summary.applications_created}", file=output)
    print(
        f"Applications already present: {summary.applications_existing}",
        file=output,
    )
    print(
        "Not Reviewed rows without history (job only): "
        f"{summary.not_reviewed_without_history}",
        file=output,
    )
    print(f"Applied rows downgraded: {summary.applied_downgraded}", file=output)
    for reason, count in sorted(summary.skipped_jobs.items()):
        print(f"Skipped job rows ({reason}): {count}", file=output)
    for reason, count in sorted(summary.skipped_applications.items()):
        print(f"Skipped application rows ({reason}): {count}", file=output)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import legacy job and application CSV data into SQLite."
    )
    parser.add_argument("--jobs-csv", required=True, type=Path)
    parser.add_argument("--applications-csv", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm-legacy-applied", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.dry_run:
        create_database_backup()
    with SessionLocal() as db:
        summary = import_csv_rows(
            db,
            args.jobs_csv,
            args.applications_csv,
            dry_run=args.dry_run,
            confirm_legacy_applied=args.confirm_legacy_applied,
        )
    print_summary(summary, output=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
