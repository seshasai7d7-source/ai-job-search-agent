from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup


USER_AGENT = "AIJobSearchAgent/1.0 (public job-board API client)"
TIMEOUT_SECONDS = 20


def _location_text(value) -> str:
    if isinstance(value, dict):
        return str(value.get("name") or value.get("location") or "")
    return str(value or "")


def _posted_date(value) -> str:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc).date().isoformat()
    return str(value or "")[:10]


def parse_ashby_jobs(payload: dict, company: str) -> list[dict]:
    jobs = []
    for item in payload.get("jobs", []):
        if item.get("isListed") is False:
            continue

        location = _location_text(item.get("location"))
        if not location:
            secondary_locations = [
                _location_text(entry)
                for entry in item.get("secondaryLocations", [])
            ]
            location = ", ".join(value for value in secondary_locations if value)

        description = item.get("descriptionPlain") or BeautifulSoup(
            item.get("descriptionHtml") or "",
            "html.parser",
        ).get_text(" ", strip=True)
        jobs.append(
            {
                "title": item.get("title", ""),
                "company": company,
                "location": location,
                "description": description,
                "skills_mentioned": "",
                "posted_date": _posted_date(item.get("publishedAt")),
                "apply_url": item.get("jobUrl", "") or "",
                "source": "",
            }
        )
    return jobs


def fetch_jobs(company: str, board_name: str) -> list[dict]:
    response = requests.get(
        f"https://api.ashbyhq.com/posting-api/job-board/{board_name}",
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return parse_ashby_jobs(response.json(), company)
