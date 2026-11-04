import requests

from job_agent.models import Job


def fetch_greenhouse_jobs(board_token, company_name):
    """
    Fetch public job listings from a Greenhouse job board.

    board_token: Company's Greenhouse job-board identifier.
    company_name: Display name of the company.
    """
    url = (
        f"https://boards-api.greenhouse.io/v1/boards/"
        f"{board_token}/jobs?content=true"
    )

    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as error:
        print(f"Could not fetch jobs for {company_name}: {error}")
        return []

    jobs = []

    for item in data.get("jobs", []):
        location_data = item.get("location") or {}
        location = location_data.get("name", "")

        content = item.get("content", "")

        jobs.append(
            Job(
                title=item.get("title", ""),
                company=company_name,
                location=location,
                url=item.get("absolute_url", ""),
                description=content,
                source="Greenhouse",
            ).to_dict()
        )

    return jobs