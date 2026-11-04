
import re

from job_agent.filters import (
    filter_jobs,
    load_config,
    calculate_skill_score,
    clean_html,
    detect_related_concepts,
    create_job_group,
)

from job_agent.sources.greenhouse import fetch_greenhouse_jobs
from job_agent.sources.lever import fetch_lever_jobs
from job_agent.storage import save_jobs


def classify_experience(job):
    """Classify job experience requirements."""

    title = job.get("title", "").lower()
    description = clean_html(job.get("description", "")).lower()

    text = title + " " + description

    experienced_patterns = [
        r"\bsoftware engineer ii\b",
        r"\bsenior\b",
        r"\bstaff\b",
        r"\bprincipal\b",
        r"\blead\b",
        r"\bmanager\b",
        r"\bminimum of\s+[3-9]\+?\s+years?\b",
        r"\bat least\s+[3-9]\+?\s+years?\b",
        r"\b[3-9]\+?\s+years?\s+of experience\b",
    ]

    if any(re.search(pattern, text) for pattern in experienced_patterns):
        return "Experience Required"

    fresher_patterns = [
        r"\bnew grad(?:uate)?s?\b",
        r"\bentry.level\b",
        r"\bfresher\b",
        r"\brecent graduates?\b",
        r"\bgraduate program\b",
        r"\bearly career\b",
        r"\bintern(ship)?\b",
        r"\bno experience required\b",
        r"\b0\s*(?:-|–|to)\s*2 years?\b",
        r"\bno more than\s+18 months\b",
        r"\bexcluding internship experience\b",
    ]

    if any(re.search(pattern, text) for pattern in fresher_patterns):
        return "Fresher Friendly"

    if "junior" in title:
        return "Junior - Verify Requirements"

    return "Needs Review"


def classify_location(job):
    """Classify job location and possible India eligibility."""

    location = job.get("location", "").lower().strip()
    description = clean_html(job.get("description", "")).lower()

    india_keywords = [
        "india", "bengaluru", "bangalore", "hyderabad",
        "chennai", "pune", "mumbai", "delhi", "noida",
        "gurugram", "gurgaon", "kolkata", "ahmedabad",
        "coimbatore", "kochi", "jaipur"
    ]

    remote_keywords = [
        "remote", "work from home", "fully remote"
    ]

    if any(city in location for city in india_keywords):
        return "Eligible - India"

    if any(word in location for word in remote_keywords):

        worldwide_terms = [
            "remote worldwide",
            "work from anywhere",
            "remote - anywhere",
            "remote anywhere",
            "open to applicants worldwide"
        ]

        if any(term in description for term in worldwide_terms):
            return "Verify - Worldwide Remote"

        return "Verify - Country Restrictions"

    return "Needs Review"


def classify_eligibility(job):
    """Determine whether an Indian applicant may be eligible."""

    location_status = job.get("location_status", "")

    if location_status == "Eligible - India":
        return "Eligible - India"

    if location_status == "Verify - Worldwide Remote":
        return "Verify - Worldwide Eligibility"

    if location_status == "Verify - Country Restrictions":
        return "Verify - Country Restrictions"

    return "Needs Review"


def calculate_priority(job):
    """Calculate application priority using score and classifications."""

    score = job.get("skill_score", 0)
    experience = job.get("experience_status")
    location = job.get("location_status")

    if experience == "Experience Required":
        return "Low"

    if location == "Needs Review":
        return "Low"

    if location in [
        "Verify - Worldwide Remote",
        "Verify - Country Restrictions"
    ]:
        return "Medium" if score >= 20 else "Low"

    if experience == "Fresher Friendly" and location == "Eligible - India":
        return "High" if score >= 30 else "Medium"

    if experience == "Junior - Verify Requirements":
        return "Medium" if score >= 30 else "Low"

    return "Medium" if score >= 20 else "Low"


def main():
    config = load_config()
    all_jobs = []

    companies = config.get("companies", {})

    # Fetch Greenhouse jobs
    for company in companies.get("greenhouse", []):
        name = company.get("name", "")
        token = company.get("board_token", "")

        if not name or not token:
            continue

        print(f"Fetching Greenhouse jobs from {name}...")
        all_jobs.extend(fetch_greenhouse_jobs(token, name))

    # Fetch Lever jobs
    for company in companies.get("lever", []):
        name = company.get("name", "")
        slug = company.get("slug", "")

        if not name or not slug:
            continue

        print(f"Fetching Lever jobs from {name}...")
        all_jobs.extend(fetch_lever_jobs(slug, name))

    print(f"\nTotal jobs fetched: {len(all_jobs)}")

    # Apply job filters
    matching_jobs = filter_jobs(all_jobs, config)

    print(f"Jobs matching your filters: {len(matching_jobs)}")

    skills = config.get("skills", [])

    # Calculate scores and classifications
    for job in matching_jobs:

        result = calculate_skill_score(job, skills)

        job["skill_score"] = result["skill_score"]
        job["matched_skills"] = result["matched_skills"]
        job["related_concepts"] = ", ".join(
            detect_related_concepts(job)
        )
        job["job_group"] = create_job_group(job)
        job["programming_score"] = result["category_scores"]["programming"]
        job["backend_score"] = result["category_scores"]["backend"]
        job["database_score"] = result["category_scores"]["database"]
        job["ai_genai_score"] = result["category_scores"]["ai_genai"]
        job["testing_tools_score"] = result["category_scores"]["testing_tools"]

        job["experience_status"] = classify_experience(job)

        job["location_status"] = classify_location(job)

        job["application_eligibility"] = classify_eligibility(job)

        job["application_priority"] = calculate_priority(job)

    # Sort by application priority and skill score
    priority_order = {
        "High": 3,
        "Medium": 2,
        "Low": 1,
    }

    matching_jobs.sort(
        key=lambda job: (
            priority_order[job["application_priority"]],
            job["skill_score"],
        ),
        reverse=True,
    )

    # Save results
    save_jobs(matching_jobs)


if __name__ == "__main__":
    main()
