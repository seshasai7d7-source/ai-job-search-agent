import os
import pandas as pd


def save_jobs(jobs, output_file="jobs.csv"):
    """Save job listings to CSV without duplicate URLs."""

    columns = [
        "title",
        "company",
        "location",
        "url",
        "description",
        "source",
        "skill_score",
        "matched_skills",
        "experience_status",
        "location_status",
        "application_eligibility",
        "application_priority",
        "programming_score",
        "backend_score",
        "database_score",
        "ai_genai_score",
        "testing_tools_score",
        "related_concepts",
        "job_group",
    ]

    if not jobs:
        print("No matching jobs found.")
        return

    new_jobs = pd.DataFrame(jobs)

    for column in columns:
        if column not in new_jobs.columns:
            new_jobs[column] = ""

    new_jobs = new_jobs[columns]
    new_jobs = new_jobs.drop_duplicates(subset=["url"])

    if os.path.exists(output_file):
        try:
            existing_jobs = pd.read_csv(output_file).fillna("")

            for column in columns:
                if column not in existing_jobs.columns:
                    existing_jobs[column] = ""

            existing_jobs = existing_jobs[columns]

            combined_jobs = pd.concat(
                [existing_jobs, new_jobs],
                ignore_index=True
            )

        except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError):
            combined_jobs = new_jobs
    else:
        combined_jobs = new_jobs

    combined_jobs = combined_jobs.drop_duplicates(
        subset=["url"],
        keep="last"
    )

    combined_jobs.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig"
    )

    print(f"Saved {len(combined_jobs)} unique jobs to {output_file}.")