from datetime import timezone

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.models import Job


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_database_schema_has_spec_tables(client):
    table_names = set(inspect(client.app.state.test_engine).get_table_names())

    assert table_names == {
        "jobs",
        "search_runs",
        "resume_profiles",
        "job_matches",
        "applications",
        "application_events",
        "drafts",
    }


def test_job_timestamps_are_utc(client):
    with Session(client.app.state.test_engine) as db:
        job = Job(
            dedupe_key="https://example.com/job",
            title="Python Developer",
            company="Example",
            source="greenhouse:example",
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        assert job.first_seen_at.tzinfo == timezone.utc
        assert job.last_seen_at.tzinfo == timezone.utc
