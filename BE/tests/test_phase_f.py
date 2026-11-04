import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Draft, Job, ResumeProfile
from app.services.drafting import build_draft_body, create_draft


def _insert_job(db):
    job = Job(
        dedupe_key="https://example.com/draft-job",
        title="Backend Engineer",
        company="Example Inc",
        location="Bengaluru, India",
        description="Python and FastAPI development.",
        source="greenhouse:example",
        apply_url="https://example.com/draft-job",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _insert_profile(db, *, approved=True):
    profile = ResumeProfile(
        skills=json.dumps(["Python", "FastAPI"]),
        projects=json.dumps(["Built a documented API project."]),
        education_lines=json.dumps(["Bachelor of Computer Science."]),
        experience_lines=json.dumps(["Backend Intern at Example"]),
        summary="Python backend engineer with internship experience.",
        approved=approved,
        is_current=True,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def test_template_draft_uses_only_profile_facts_and_visible_placeholders(client):
    with Session(client.app.state.test_engine) as db:
        job = _insert_job(db)
        profile = _insert_profile(db)

        body = build_draft_body("cover_letter", job, profile)

    assert "Backend Engineer" in body
    assert "Example Inc" in body
    assert "Python, FastAPI" in body
    assert "Built a documented API project." in body
    assert "Bachelor of Computer Science." in body
    assert "[ADD: Your name]" in body
    assert "invented employer" not in body


def test_answer_draft_uses_question_and_approved_profile_facts(client):
    with Session(client.app.state.test_engine) as db:
        job = _insert_job(db)
        profile = _insert_profile(db)

        draft = create_draft("answer", job, profile, "Why are you a fit?")

    assert "Why are you a fit?" in draft.body
    assert "Python backend engineer with internship experience." in draft.body
    assert "Backend Intern at Example" in draft.body


def test_draft_service_requires_approved_current_profile(client):
    with Session(client.app.state.test_engine) as db:
        job = _insert_job(db)
        unapproved = _insert_profile(db, approved=False)

        try:
            create_draft("cover_letter", job, unapproved)
        except ValueError as exc:
            assert "approved current" in str(exc)
        else:
            raise AssertionError("Draft generation must require an approved profile.")


def test_draft_endpoint_requires_approved_profile_and_existing_job(client):
    assert (
        client.post(
            "/jobs/1/drafts",
            json={"kind": "cover_letter"},
        ).status_code
        == 404
    )

    with Session(client.app.state.test_engine) as db:
        job = _insert_job(db)
        job_id = job.id
        _insert_profile(db, approved=False)

    response = client.post(
        f"/jobs/{job_id}/drafts",
        json={"kind": "cover_letter"},
    )
    assert response.status_code == 409
    assert "approved" in response.json()["detail"]


def test_draft_edit_and_approve_are_separate_and_user_controlled(client):
    with Session(client.app.state.test_engine) as db:
        job = _insert_job(db)
        job_id = job.id
        _insert_profile(db)

    created = client.post(
        f"/jobs/{job_id}/drafts",
        json={"kind": "cover_letter"},
    )
    assert created.status_code == 201
    draft_id = created.json()["id"]
    assert created.json()["status"] == "draft"

    edited = client.patch(
        f"/drafts/{draft_id}",
        json={"body": "User-edited cover letter."},
    )
    assert edited.status_code == 200
    assert edited.json()["body"] == "User-edited cover letter."

    approved = client.post(f"/drafts/{draft_id}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved_by_user"
    assert client.patch(
        f"/drafts/{draft_id}",
        json={"body": "Cannot update after approval."},
    ).status_code == 409
    assert client.get(f"/jobs/{job_id}/drafts").json()[0]["id"] == draft_id

    with Session(client.app.state.test_engine) as db:
        assert db.scalar(select(Draft).where(Draft.id == draft_id)).body == "User-edited cover letter."


def test_answer_draft_requires_question_and_missing_records_return_404(client):
    with Session(client.app.state.test_engine) as db:
        job = _insert_job(db)
        job_id = job.id
        _insert_profile(db)

    missing_question = client.post(
        f"/jobs/{job_id}/drafts",
        json={"kind": "answer"},
    )
    assert missing_question.status_code == 422
    assert client.get("/jobs/999/drafts").status_code == 404
    assert client.patch("/drafts/999", json={"body": "text"}).status_code == 404
    assert client.post("/drafts/999/approve").status_code == 404


def test_no_endpoint_submits_jobs_or_sends_messages(client):
    route_names = {
        route.path.lower()
        for route in client.app.routes
        if hasattr(route, "path")
    }

    assert not any("submit" in route or "send" in route for route in route_names)
