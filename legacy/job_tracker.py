import os
import pandas as pd

INPUT_FILE = "recommended_jobs.csv"
TRACKER_FILE = "application_tracker.csv"


def create_tracker():
    jobs = pd.read_csv(INPUT_FILE).fillna("")

    # Load the existing tracker so application progress is preserved.
    if os.path.exists(TRACKER_FILE):
        tracker = pd.read_csv(TRACKER_FILE, dtype=str).fillna("")

        if "url" in tracker.columns:
            existing_urls = set(tracker["url"].astype(str))
        else:
            existing_urls = set()

        new_jobs = jobs[~jobs["url"].astype(str).isin(existing_urls)].copy()

        if not new_jobs.empty:
            tracker = pd.concat(
                [tracker, new_jobs],
                ignore_index=True,
                sort=False,
            )
    else:
        tracker = jobs.copy()

    # Add editable tracking fields without overwriting existing progress.
    defaults = {
        "india_eligibility": "Not Verified",
        "fresher_eligibility": "Not Verified",
        "missing_skills": "",
        "eligibility_notes": "",
        "application_status": "Not Reviewed",
        "application_date": "",
        "follow_up_date": "",
    }

    for column, default_value in defaults.items():
        if column not in tracker.columns:
            tracker[column] = default_value
        else:
            tracker[column] = (
                tracker[column]
                .fillna("")
                .astype(str)
                .str.strip()
                .replace("", default_value)
            )

    tracker.to_csv(TRACKER_FILE, index=False, encoding="utf-8-sig")

    print(f"\nTracker saved to: {TRACKER_FILE}")
    print(f"Total tracked postings: {len(tracker)}")

    print("\nApplication status summary:")
    print(tracker["application_status"].value_counts().to_string())

    print("\nJobs to review:")
    columns = [
        "title",
        "company",
        "location",
        "recommendation",
        "india_eligibility",
        "fresher_eligibility",
        "application_status",
        "url",
    ]

    print(tracker[columns].to_string(index=False))


if __name__ == "__main__":
    create_tracker()