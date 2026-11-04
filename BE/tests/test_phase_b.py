import json
import yaml
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Job, SearchRun
from app.routers import search as search_router
from app.services.job_store import create_dedupe_key, upsert_jobs
from app.services.search import run_search
from app.sources.greenhouse import parse_greenhouse_jobs
from app.sources.lever import parse_lever_jobs


def _job(**overrides):
    job = {
        "title": "Python Developer",
        "company": "Example",
        "location": "Bengaluru, India",
        "description": "Python and FastAPI developer. No experience required.",
        "skills_mentioned": "Python, FastAPI",
        "posted_date": "",
        "apply_url": "https://example.com/job/1/",
        "source": "",
    }
    job.update(overrides)
    return job


def test_source_parsers_preserve_apply_url_and_normalize_shapes():
    greenhouse = parse_greenhouse_jobs(
        {
            "jobs": [
                {
                    "title": "Python Developer",
                    "location": {"name": "Bengaluru, India"},
                    "content": "<p>Python role</p>",
                    "absolute_url": "https://boards.greenhouse.io/acme/jobs/10",
                    "updated_at": "2026-01-02T03:04:05Z",
                }
            ]
        },
        "Acme",
    )[0]
    lever = parse_lever_jobs(
        [
            {
                "text": "Backend Developer",
                "categories": {"location": "Remote - India"},
                "descriptionPlain": "Build APIs",
                "hostedUrl": "https://jobs.lever.co/acme/abc",
                "createdAt": 1760000000000,
            }
        ],
        "Acme",
    )[0]

    assert greenhouse["apply_url"] == "https://boards.greenhouse.io/acme/jobs/10"
    assert greenhouse["description"] == "Python role"
    assert set(greenhouse) == set(lever)
    assert lever["apply_url"] == "https://jobs.lever.co/acme/abc"


def test_search_run_fetches_configured_ashby_source(client, monkeypatch, tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "search": {
                    "roles": ["Python Developer"],
                    "locations": ["India"],
                    "experience_keywords": ["junior"],
                },
                "skills": ["Python"],
                "companies": {
                    "ashby": [{"name": "Example", "board_name": "example"}],
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "app.services.search.ashby.fetch_jobs",
        lambda company, identifier: [_job(company=company)],
    )

    with Session(client.app.state.test_engine) as db:
        run = SearchRun(status="running")
        db.add(run)
        db.commit()

        run_search(db, run.id, config_path=config_path)
        db.refresh(run)
        stored_job = db.scalar(select(Job))

        assert run.status == "done"
        assert json.loads(run.per_source_results)["ashby:example"]["new_jobs"] == 1
        assert stored_job.source == "ashby:example"


def test_dedupe_key_and_upsert_keep_first_seen_and_update_last_seen(client):
    assert create_dedupe_key(_job()) == "https://example.com/job/1"
    with Session(client.app.state.test_engine) as db:
        created, seen = upsert_jobs(db, [_job()], "greenhouse:example")
        db.commit()
        stored = db.scalar(select(Job))
        first_seen = stored.first_seen_at

        created_again, _ = upsert_jobs(
            db,
            [_job(title="Changed title", description="Changed description")],
            "greenhouse:example",
        )
        db.commit()
        db.refresh(stored)

        assert created == 1
        assert created_again == 0
        assert seen == {"https://example.com/job/1"}
        assert stored.first_seen_at == first_seen
        assert stored.last_seen_at >= first_seen
        assert stored.title == "Python Developer"
        assert db.scalar(select(func.count()).select_from(Job)) == 1


def test_search_run_isolates_source_failures_and_deduplicates(client, monkeypatch, tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "search": {
                    "roles": ["Python Developer"],
                    "locations": ["India", "Bengaluru"],
                    "experience_keywords": ["fresher", "junior"],
                },
                "skills": ["Python", "FastAPI"],
                "companies": {
                    "greenhouse": [{"name": "Example", "board_token": "example"}],
                    "lever": [{"name": "Failing", "slug": "failing"}],
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "app.services.search.greenhouse.fetch_jobs",
        lambda company, identifier: [_job(company=company)],
    )

    def fail_lever(company, identifier):
        raise RuntimeError("source unavailable")

    monkeypatch.setattr("app.services.search.lever.fetch_jobs", fail_lever)

    with Session(client.app.state.test_engine) as db:
        run = SearchRun(status="running")
        db.add(run)
        db.commit()
        run_id = run.id

        run_search(db, run_id, config_path=config_path)
        db.refresh(run)
        first_finished = run.finished_at
        first_result = json.loads(run.per_source_results)

        assert run.status == "done"
        assert run.new_jobs == 1
        assert first_result["greenhouse:example"]["new_jobs"] == 1
        assert first_result["lever:failing"]["error"] == "source unavailable"

        run_again = SearchRun(status="running")
        db.add(run_again)
        db.commit()
        run_search(db, run_again.id, config_path=config_path)
        db.refresh(run_again)
        stored_job = db.scalar(select(Job))
        assert run_again.new_jobs == 0
        assert stored_job.is_active is True
        assert stored_job.first_seen_at <= first_finished


def test_successful_empty_source_deactivates_jobs_but_failed_source_does_not(
    client, monkeypatch, tmp_path
):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "search": {"roles": [], "locations": [], "experience_keywords": []},
                "companies": {
                    "greenhouse": [{"name": "Example", "board_token": "example"}],
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "app.services.search.greenhouse.fetch_jobs",
        lambda company, identifier: [],
    )
    with Session(client.app.state.test_engine) as db:
        _, _ = upsert_jobs(db, [_job()], "greenhouse:example")
        db.commit()
        run = SearchRun(status="running")
        db.add(run)
        db.commit()

        run_search(db, run.id, config_path=config_path)
        stored = db.scalar(select(Job))
        assert stored.is_active is False


def test_search_routes_create_runs_and_return_missing_ids(client, monkeypatch):
    monkeypatch.setattr(search_router, "_run_search_background", lambda run_id: None)

    response = client.post("/search-runs")
    assert response.status_code == 202
    run_id = response.json()["id"]

    assert client.get(f"/search-runs/{run_id}").status_code == 200
    assert client.get("/search-runs/999").status_code == 404
    assert client.get("/jobs").status_code == 200
    assert client.get("/jobs/999").status_code == 404
    assert client.get("/config").status_code == 200


def test_job_list_query_filters(client):
    with Session(client.app.state.test_engine) as db:
        db.add_all(
            [
                Job(
                    dedupe_key="https://example.com/a",
                    title="Python Developer",
                    company="Acme",
                    location="Bengaluru, India",
                    description="Python APIs",
                    apply_url="https://example.com/a",
                    source="greenhouse:acme",
                ),
                Job(
                    dedupe_key="https://example.com/b",
                    title="Data Analyst",
                    company="Other",
                    location="London",
                    description="Data analysis",
                    apply_url="https://example.com/b",
                    source="lever:other",
                ),
            ]
        )
        db.commit()

    response = client.get("/jobs", params={"role": "Python", "company": "Acme"})
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["apply_url"] == "https://example.com/a"
