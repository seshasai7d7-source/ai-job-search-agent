from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup


USER_AGENT = "AIJobSearchAgent/1.0 (public job-board API client)"
TIMEOUT_SECONDS = 20


def _posted_date(value) -> str:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc).date().isoformat()
    return str(value or "")[:10]


def parse_lever_jobs(payload: list[dict], company: str) -> list[dict]:
    jobs = []
    for item in payload:
        categories = item.get("categories") or {}
        description_parts = [item.get("descriptionPlain", "")]

        for section in item.get("lists", []):
            description_parts.append(section.get("text", ""))
            description_parts.append(
                BeautifulSoup(section.get("content", ""), "html.parser").get_text(" ", strip=True)
            )

        description_parts.append(item.get("additionalPlain", ""))
        jobs.append(
            {
                "title": item.get("text", ""),
                "company": company,
                "location": categories.get("location", ""),
                "description": "\n\n".join(part for part in description_parts if part),
                "skills_mentioned": "",
                "posted_date": _posted_date(item.get("createdAt")),
                "apply_url": item.get("hostedUrl", "") or "",
                "source": "",
            }
        )
    return jobs


def fetch_jobs(company: str, slug: str) -> list[dict]:
    response = requests.get(
        f"https://api.lever.co/v0/postings/{slug}?mode=json",
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return parse_lever_jobs(response.json(), company)
