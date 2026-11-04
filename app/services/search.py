import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import load_search_config
from app.models import SearchRun
from app.services.filters import filter_jobs
from app.services.job_store import deactivate_missing_jobs, upsert_jobs
from app.services.skills import extract_skills
from app.sources import ashby, greenhouse, lever


logger = logging.getLogger(__name__)


def configured_sources(config: dict) -> list[tuple[str, dict]]:
    companies = config.get("companies", {})
    configured = []
    for company in companies.get("greenhouse", []):
        if company.get("name") and company.get("board_token"):
            configured.append((f"greenhouse:{company['board_token']}", company))
    for company in companies.get("lever", []):
        if company.get("name") and company.get("slug"):
            configured.append((f"lever:{company['slug']}", company))
    for company in companies.get("ashby", []):
        if company.get("name") and company.get("board_name"):
            configured.append((f"ashby:{company['board_name']}", company))
    return configured


def run_search(db: Session, run_id: int, config_path=None) -> None:
    run = db.get(SearchRun, run_id)
    if run is None:
        return

    config = load_search_config(config_path)
    results = {}
    total_new_jobs = 0
    any_success = False

    for source_key, company in configured_sources(config):
        provider, identifier = source_key.split(":", 1)
        try:
            if provider == "greenhouse":
                fetched = greenhouse.fetch_jobs(company["name"], identifier)
            elif provider == "lever":
                fetched = lever.fetch_jobs(company["name"], identifier)
            elif provider == "ashby":
                fetched = ashby.fetch_jobs(company["name"], identifier)
            else:
                continue

            for job in fetched:
                job["source"] = source_key
                job["skills_mentioned"] = ", ".join(
                    extract_skills(job.get("description", ""), config.get("skills", []))
                )
            kept = filter_jobs(fetched, config.get("search", {}))
            new_count, seen_keys = upsert_jobs(db, kept, source_key)
            deactivate_missing_jobs(db, source_key, seen_keys)
            db.commit()
            total_new_jobs += new_count
            any_success = True
            results[source_key] = {
                "fetched": len(fetched),
                "kept": len(kept),
                "new_jobs": new_count,
                "error": None,
            }
        except Exception as exc:
            db.rollback()
            logger.warning("Job source %s failed: %s", source_key, type(exc).__name__)
            results[source_key] = {
                "fetched": 0,
                "kept": 0,
                "new_jobs": 0,
                "error": str(exc)[:500],
            }

    run = db.get(SearchRun, run_id)
    if run is None:
        return
    run.finished_at = datetime.now(timezone.utc)
    run.status = "done" if any_success or not results else "failed"
    run.per_source_results = json.dumps(results)
    run.new_jobs = total_new_jobs
    db.commit()
