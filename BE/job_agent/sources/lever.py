import requests

from job_agent.models import Job


def fetch_lever_jobs(company_slug, company_name):
    """
    Fetch publicly available job listings from a Lever job board.

    company_slug: Company's Lever site identifier.
    company_name: Display name of the company.
    """
    url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"

    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as error:
        print(f"Could not fetch jobs for {company_name}: {error}")
        return []

    jobs = []

    for item in data:
        categories = item.get("categories") or {}
        location = categories.get("location", "")

        description = item.get("descriptionPlain", "")

        additional = item.get("additional", "")
        if additional:
            description += "\n" + additional

        jobs.append(
            Job(
                title=item.get("text", ""),
                company=company_name,
                location=location,
                url=item.get("hostedUrl", ""),
                description=description,
                source="Lever",
            ).to_dict()
        )

    return jobs