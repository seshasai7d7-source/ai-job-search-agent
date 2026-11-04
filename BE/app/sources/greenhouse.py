import requests
from bs4 import BeautifulSoup


USER_AGENT = "AIJobSearchAgent/1.0 (public job-board API client)"
TIMEOUT_SECONDS = 20


def parse_greenhouse_jobs(payload: dict, company: str) -> list[dict]:
    jobs = []
    for item in payload.get("jobs", []):
        location = item.get("location") or {}
        jobs.append(
            {
                "title": item.get("title", ""),
                "company": company,
                "location": location.get("name", "") if isinstance(location, dict) else str(location),
                "description": BeautifulSoup(
                    item.get("content", "") or "", "html.parser"
                ).get_text(" ", strip=True),
                "skills_mentioned": "",
                "posted_date": "",
                "apply_url": item.get("absolute_url", "") or "",
                "source": "",
            }
        )
    return jobs


def fetch_jobs(company: str, board_token: str) -> list[dict]:
    response = requests.get(
        f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true",
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return parse_greenhouse_jobs(response.json(), company)
