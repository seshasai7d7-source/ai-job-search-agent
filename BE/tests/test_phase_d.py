import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Job, JobMatch, ResumeProfile
from app.services.matching import calculate_skills_overlap
from app.services.skills import extract_canonical_skills


def _approved_profile(db, skills):
    profile = ResumeProfile(
        skills=json.dumps(skills),
        approved=True,
        is_current=True,
        warnings="[]",
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def _job(db, dedupe_key, description):
    job = Job(
        dedupe_key=dedupe_key,
        title="Python Developer",
        company="Example",
        location="Bengaluru, India",
        description=description,
        source="greenhouse:example",
        is_active=True,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def test_extract_canonical_skills_resolves_aliases_and_duplicates():
    skills = extract_canonical_skills(
        "Python, JS, PostgreSQL, REST APIs, and JavaScript.",
        ["Python", "JavaScript", "PostgreSQL", "REST API", "REST APIs"],
    )

    assert skills == ["Python", "JavaScript", "PostgreSQL", "REST API"]


def test_skills_overlap_formula_and_empty_job_skills():
    overlap, matched, missing = calculate_skills_overlap(
        ["Python", "FastAPI", "unknown"], ["Python"]
    )
    no_score, no_matched, no_missing = calculate_skills_overlap(
        ["unknown"], ["Python"]
    )

    assert overlap == 50.0
    assert matched == ["Python"]
    assert missing == ["FastAPI"]
    assert no_score is None
    assert no_matched == []
    assert no_missing == []


def test_recompute_matches_requires_approved_profile(client):
    assert client.post("/matches/recompute").status_code == 409
    assert client.get("/jobs/999/match").status_code == 404


def test_recompute_and_get_job_match(client):
    with Session(client.app.state.test_engine) as db:
        profile = _approved_profile(db, ["Python", "FastAPI"])
        job = _job(db, "https://example.com/matching", "Python, FastAPI, and SQL.")
        job_id = job.id
        profile_id = profile.id

    response = client.post("/matches/recompute")
    assert response.status_code == 200
    assert response.json()["computed_jobs"] == 1
    assert response.json()["label"] == "Skills overlap"

    match_response = client.get(f"/jobs/{job_id}/match")
    assert match_response.status_code == 200
    assert match_response.json()["skills_overlap"] == 66.7
    assert match_response.json()["matched_skills"] == ["Python", "FastAPI"]
    assert match_response.json()["missing_skills"] == ["SQL"]

    with Session(client.app.state.test_engine) as db:
        assert db.scalar(select(JobMatch).where(JobMatch.profile_id == profile_id))


def test_job_list_includes_match_and_min_overlap_filter(client):
    with Session(client.app.state.test_engine) as db:
        _approved_profile(db, ["Python", "FastAPI"])
        first = _job(db, "https://example.com/low", "Python and SQL.")
        second = _job(db, "https://example.com/high", "Python and FastAPI.")
        first_id = first.id
        second_id = second.id
        from app.services.matching import match_job_to_profile

        profile = db.scalar(
            select(ResumeProfile).where(ResumeProfile.approved.is_(True))
        )
        match_job_to_profile(db, first, profile)
        match_job_to_profile(db, second, profile)
        db.commit()

    response = client.get("/jobs", params={"min_overlap": 70})
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [second_id]

    detail = client.get(f"/jobs/{first_id}")
    assert detail.status_code == 200
    assert detail.json()["skills_overlap"] == 50.0


def test_min_overlap_requires_approved_profile(client):
    assert client.get("/jobs", params={"min_overlap": 0}).status_code == 409
