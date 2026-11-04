import io
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.models import Application, ApplicationEvent, Base, Job
from scripts import import_csv_to_db
from scripts.import_csv_to_db import import_csv_rows, print_summary


FIXTURES = Path(__file__).parent / "fixtures"
JOBS_CSV = FIXTURES / "legacy_jobs.csv"
APPLICATIONS_CSV = FIXTURES / "legacy_applications.csv"


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    yield factory
    engine.dispose()


def _counts(session_factory):
    with session_factory() as db:
        return (
            db.scalar(select(func.count()).select_from(Job)),
            db.scalar(select(func.count()).select_from(Application)),
            db.scalar(select(func.count()).select_from(ApplicationEvent)),
        )


def _run(session_factory, *, dry_run=False, confirm_legacy_applied=False):
    with session_factory() as db:
        return import_csv_rows(
            db,
            JOBS_CSV,
            APPLICATIONS_CSV,
            dry_run=dry_run,
            confirm_legacy_applied=confirm_legacy_applied,
        )


def test_dry_run_counts_imports_but_rolls_back_and_summary_has_no_row_data(
    session_factory,
):
    before = _counts(session_factory)
    summary = _run(session_factory, dry_run=True)
    after = _counts(session_factory)
    output = io.StringIO()
    print_summary(summary, output)

    assert before == after == (0, 0, 0)
    assert summary.jobs_created == 6
    assert summary.skipped_jobs == {"missing_url": 1}
    assert summary.applications_created == 5
    assert summary.not_reviewed_without_history == 1
    assert summary.applied_downgraded == 1
    assert summary.skipped_applications == {
        "missing_url": 1,
        "unsupported_status": 2,
    }
    assert "Synthetic" not in output.getvalue()
    assert "Fixture Co" not in output.getvalue()
    assert "example.invalid" not in output.getvalue()
    assert "Fixture description" not in output.getvalue()


def test_import_is_idempotent_and_never_overwrites_existing_application(
    session_factory,
):
    first = _run(session_factory)
    with session_factory() as db:
        applied_job = db.scalar(
            select(Job).where(Job.apply_url == "https://example.invalid/job/existing")
        )
        application = db.scalar(
            select(Application).where(Application.job_id == applied_job.id)
        )
        original_notes = application.notes
        original_status = application.status
        application.notes = "Keep this existing note."
        db.commit()

    second = _run(session_factory)

    assert first.applications_created == 5
    assert second.jobs_created == 0
    assert second.applications_created == 0
    assert second.applications_existing == 5
    with session_factory() as db:
        application = db.scalar(
            select(Application).where(Application.job_id == applied_job.id)
        )
        assert application.status == original_status
        assert application.notes == "Keep this existing note."
        assert application.notes != original_notes
        assert db.scalar(select(func.count()).select_from(ApplicationEvent)) == 5


@pytest.mark.parametrize(
    ("confirm", "expected_status", "expected_confirmation"),
    [
        (False, "Application Prepared", False),
        (True, "Applied", True),
    ],
)
def test_applied_legacy_rows_follow_explicit_confirmation(
    session_factory,
    confirm,
    expected_status,
    expected_confirmation,
):
    _run(session_factory, confirm_legacy_applied=confirm)
    with session_factory() as db:
        job = db.scalar(
            select(Job).where(Job.apply_url == "https://example.invalid/job/existing")
        )
        application = db.scalar(
            select(Application).where(Application.job_id == job.id)
        )
        event = db.scalar(
            select(ApplicationEvent).where(
                ApplicationEvent.application_id == application.id
            )
        )

        assert application.status == expected_status
        assert event.to_status == expected_status
        assert event.confirmed_by_user is expected_confirmation


def test_legacy_statuses_notes_and_not_reviewed_rules(session_factory):
    _run(session_factory)
    with session_factory() as db:
        applications = {
            job.apply_url: application
            for application, job in db.execute(
                select(Application, Job).join(Job, Application.job_id == Job.id)
            )
        }
        assert "https://example.invalid/job/untouched" not in applications
        untouched_job = db.scalar(
            select(Job).where(
                Job.apply_url == "https://example.invalid/job/untouched"
            )
        )
        assert untouched_job is not None
        assert untouched_job.title == "Synthetic Untouched Job"
        assert not hasattr(untouched_job, "skill_score")

        eligibility = applications["https://example.invalid/job/eligibility"]
        assert eligibility.status == "Interested"
        assert "legacy india_eligibility: Eligible" in eligibility.notes
        assert (
            "legacy application_eligibility: Synthetic application eligibility"
            in eligibility.notes
        )

        verification = applications["https://example.invalid/job/verify"]
        assert verification.status == "Interested"
        assert "legacy status: Needs Verification" in verification.notes
        assert "legacy eligibility_notes: check official listing" in verification.notes
        assert "legacy experience_requirement: 0-1 Years" in verification.notes

        assert applications["https://example.invalid/job/ready"].status == (
            "Application Prepared"
        )
        rejected = applications["https://example.invalid/job/rejected"]
        assert rejected.status == "Rejected"
        assert "legacy application_date: 2026-01-02" in rejected.notes
        assert "legacy follow_up_date: 2026-01-09" in rejected.notes
        assert db.scalar(select(func.count()).select_from(ApplicationEvent)) == 5
        assert all(
            event.note == "Imported from legacy CSV"
            for event in db.scalars(select(ApplicationEvent))
        )


def test_backup_is_created_and_existing_timestamp_is_never_overwritten(
    tmp_path,
    monkeypatch,
):
    source_path = tmp_path / "source.db"
    with sqlite3.connect(source_path) as db:
        db.execute("CREATE TABLE sample (value TEXT)")
        db.execute("INSERT INTO sample VALUES ('snapshot')")

    monkeypatch.setattr(import_csv_to_db, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(import_csv_to_db, "_database_file", lambda: source_path)
    timestamp = datetime(2026, 11, 4, tzinfo=timezone.utc)

    backup_path = import_csv_to_db.create_database_backup(timestamp)
    with sqlite3.connect(backup_path) as backup:
        value = backup.execute("SELECT value FROM sample").fetchone()[0]
    assert value == "snapshot"

    with pytest.raises(FileExistsError):
        import_csv_to_db.create_database_backup(timestamp)
