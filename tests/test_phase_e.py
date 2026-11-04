from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Application, ApplicationEvent, Job
from app.services.applications import RuleViolation, check_transition


def _create_job(db):
    job = Job(
        dedupe_key="https://example.com/application-job",
        title="Python Developer",
        company="Example",
        location="Bengaluru, India",
        source="greenhouse:example",
        apply_url="https://example.com/application-job",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def test_transition_rules_require_confirmation_for_applied():
    try:
        check_transition("Interested", "Applied", False)
    except RuleViolation as exc:
        assert "confirmed_by_user=true" in str(exc)
    else:
        raise AssertionError("Applied transition should require user confirmation.")

    check_transition("Interested", "Applied", True)

    try:
        check_transition("Offer", "Interview", True)
    except RuleViolation:
        pass
    else:
        raise AssertionError("Invalid status transition should be rejected.")


def test_application_create_duplicate_and_not_found_job(client):
    missing_job = client.post("/applications", json={"job_id": 500})
    assert missing_job.status_code == 404

    with Session(client.app.state.test_engine) as db:
        job = _create_job(db)
        job_id = job.id

    created = client.post("/applications", json={"job_id": job_id})
    assert created.status_code == 201
    assert created.json()["status"] == "Interested"

    duplicate = client.post("/applications", json={"job_id": job_id})
    assert duplicate.status_code == 409


def test_applied_transition_requires_confirmation_and_records_events(client):
    with Session(client.app.state.test_engine) as db:
        job = _create_job(db)
        job_id = job.id

    created = client.post("/applications", json={"job_id": job_id})
    application_id = created.json()["id"]

    rejected = client.patch(
        f"/applications/{application_id}",
        json={"status": "Applied"},
    )
    assert rejected.status_code == 409
    assert client.get(f"/applications/{application_id}/events").json() == []

    applied = client.patch(
        f"/applications/{application_id}",
        json={
            "status": "Applied",
            "confirmed_by_user": True,
            "note": "Submitted on the employer site.",
        },
    )
    assert applied.status_code == 200
    assert applied.json()["status"] == "Applied"
    events = client.get(f"/applications/{application_id}/events")
    assert events.status_code == 200
    assert len(events.json()) == 1
    assert events.json()[0]["confirmed_by_user"] is True
    assert events.json()[0]["note"] == "Submitted on the employer site."

    progressed = client.patch(
        f"/applications/{application_id}",
        json={"status": "Interview", "note": "Recruiter screen"},
    )
    assert progressed.status_code == 200
    events = client.get(f"/applications/{application_id}/events").json()
    assert [event["to_status"] for event in events] == ["Applied", "Interview"]
    assert events[0]["from_status"] == "Interested"


def test_application_status_filter_and_missing_ids(client):
    with Session(client.app.state.test_engine) as db:
        job = _create_job(db)
        job_id = job.id

    created = client.post("/applications", json={"job_id": job_id})
    application_id = created.json()["id"]
    assert client.get("/applications", params={"status": "Interested"}).json()[0]["id"] == application_id
    assert client.get("/applications", params={"status": "Rejected"}).json() == []
    assert client.patch("/applications/999", json={"status": "Applied"}).status_code == 404
    assert client.get("/applications/999/events").status_code == 404


def test_illegal_transition_is_rejected_without_event(client):
    with Session(client.app.state.test_engine) as db:
        job = _create_job(db)
        job_id = job.id
    application_id = client.post("/applications", json={"job_id": job_id}).json()["id"]

    response = client.patch(
        f"/applications/{application_id}",
        json={"status": "Offer", "confirmed_by_user": True},
    )

    assert response.status_code == 409
    assert client.get(f"/applications/{application_id}/events").json() == []


def test_status_history_is_append_only_at_api_surface(client):
    with Session(client.app.state.test_engine) as db:
        job = _create_job(db)
        job_id = job.id
    application_id = client.post("/applications", json={"job_id": job_id}).json()["id"]
    client.patch(
        f"/applications/{application_id}",
        json={"status": "Application Prepared"},
    )

    assert client.post(f"/applications/{application_id}/events").status_code == 405
    assert client.delete(f"/applications/{application_id}/events").status_code == 405

    with Session(client.app.state.test_engine) as db:
        assert len(db.scalars(select(ApplicationEvent)).all()) == 1
        assert db.get(Application, application_id).status == "Application Prepared"
