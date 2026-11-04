import json
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import load_search_config
from app.database import SessionLocal, get_db
from app.models import SearchRun
from app.services.search import run_search


router = APIRouter(tags=["search"])


def _run_search_background(run_id: int) -> None:
    with SessionLocal() as db:
        run_search(db, run_id)


@router.get("/config")
def get_config():
    config = load_search_config()
    companies = config.get("companies", {})
    sources = []
    identifiers = {
        "greenhouse": "board_token",
        "lever": "slug",
        "ashby": "board_name",
    }
    for provider, identifier_key in identifiers.items():
        for company in companies.get(provider, []):
            identifier = company.get(identifier_key)
            if identifier:
                sources.append({"source": provider, "company": company.get("name", ""), "identifier": identifier})
    return {
        "roles": config.get("search", {}).get("roles", []),
        "locations": config.get("search", {}).get("locations", []),
        "sources": sources,
    }


@router.post("/search-runs", status_code=202)
def create_search_run(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    run = SearchRun(started_at=datetime.now(timezone.utc), status="running")
    db.add(run)
    db.commit()
    db.refresh(run)
    background_tasks.add_task(_run_search_background, run.id)
    return {"id": run.id, "status": run.status}


@router.get("/search-runs")
def list_search_runs(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    if limit < 1 or limit > 100 or offset < 0:
        raise HTTPException(status_code=422, detail="Invalid pagination values.")
    runs = db.scalars(
        select(SearchRun).order_by(SearchRun.started_at.desc()).limit(limit).offset(offset)
    ).all()
    return [
        {
            "id": run.id,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
            "status": run.status,
            "new_jobs": run.new_jobs,
        }
        for run in runs
    ]


@router.get("/search-runs/{run_id}")
def get_search_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(SearchRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Search run not found.")
    return {
        "id": run.id,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "status": run.status,
        "per_source_results": json.loads(run.per_source_results),
        "new_jobs": run.new_jobs,
    }
