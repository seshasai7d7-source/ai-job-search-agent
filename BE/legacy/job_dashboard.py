
from datetime import date
from pathlib import Path

import pandas as pd

TRACKER_FILE = Path("application_tracker.csv")
REPORT_FILE = Path("job_dashboard.txt")


def main():
    if not TRACKER_FILE.exists():
        print(f"Tracker not found: {TRACKER_FILE}")
        print("Run legacy/job_tracker.py first.")
        return

    df = pd.read_csv(TRACKER_FILE, dtype=str).fillna("")

    required_columns = [
        "title", "company", "location", "recommendation",
        "india_eligibility", "fresher_eligibility",
        "application_status", "application_date",
        "follow_up_date", "url"
    ]

    missing = [col for col in required_columns if col not in df.columns]

    if missing:
        print("Tracker is missing columns:", ", ".join(missing))
        return

    lines = []

    def add(text=""):
        lines.append(str(text))

    def display(value):
        return str(value).strip() if str(value).strip() else "Not available"

    add("=" * 75)
    add("                    AI JOB SEARCH DASHBOARD")
    add("=" * 75)
    add(f"Report date: {date.today().isoformat()}")
    add(f"Total job postings: {len(df)}")
    add("1. APPLICATION STATUS")
    add("-" * 75)

    status_counts = df["application_status"].replace("", "Not Reviewed")

    for status, count in status_counts.value_counts().items():
        add(f"{status}: {count}")

    add()

    # 3. Eligibility verification
    add("2. ELIGIBILITY NEEDING VERIFICATION")
    add("-" * 75)

    unverified = df[
        df["india_eligibility"].str.lower().isin(
            ["", "not verified", "unknown", "needs verification"]
        )
        | df["fresher_eligibility"].str.lower().isin(
            ["", "not verified", "unknown", "needs verification"]
        )
    ]

    if unverified.empty:
        add("No unverified eligibility fields found.")
    else:
        for _, row in unverified.iterrows():
            add(f"- {row['title']} - {row['company']}")
            add(f"  Location: {row['location']}")
            add(f"  India eligibility: {display(row['india_eligibility'])}")
            add(f"  Fresher eligibility: {display(row['fresher_eligibility'])}")
            add(f"  URL: {row['url']}")

    add()

    # 4. Priority jobs
    add("3. PRIORITY JOBS FOR MANUAL REVIEW")
    add("-" * 75)

    priority_jobs = df[
        df["recommendation"].str.lower().isin(
            ["apply first", "verify eligibility", "verify country restrictions"]
        )
    ]

    if priority_jobs.empty:
        add("No priority jobs found.")
    else:
        for _, row in priority_jobs.iterrows():
            add(
                f"- {row['title']} - {row['company']} "
                f"({row['recommendation']})"
            )
            add(f"  Location: {row['location']}")
            add(f"  Application status: {row['application_status']}")
            add(f"  URL: {row['url']}")

    add()

    # 5. Follow-ups
    add("4. FOLLOW-UPS DUE")
    add("-" * 75)

    today = date.today()
    due_rows = []

    for _, row in df.iterrows():
        follow_up = row["follow_up_date"].strip()

        if not follow_up:
            continue

        try:
            follow_up_date = date.fromisoformat(follow_up[:10])
        except ValueError:
            continue

        if follow_up_date <= today and row["application_status"] == "Applied":
            due_rows.append((row, follow_up_date))

    if not due_rows:
        add("No follow-ups are due for jobs marked Applied.")
    else:
        for row, follow_up_date in due_rows:
            add(f"- {row['title']} - {row['company']}")
            add(f"  Follow-up date: {follow_up_date.isoformat()}")
            add(f"  URL: {row['url']}")

    add()

    # 6. Application progress
    add("5. APPLICATION PROGRESS")
    add("-" * 75)

    applied = df[df["application_status"].str.lower() == "applied"]

    add(f"Applications marked Applied: {len(applied)}")

    if not applied.empty:
        for _, row in applied.iterrows():
            add(f"- {row['title']} - {row['company']}")
            add(f"  Application date: {display(row['application_date'])}")

    add()
    add("=" * 75)
    add("Skills overlap is advisory and is not a hiring prediction.")
    add("Remote does not automatically mean eligible to work from India.")
    add("Verify country and fresher eligibility on official job pages.")
    add("=" * 75)

    REPORT_FILE.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )

    print(f"Dashboard generated: {REPORT_FILE}")
    print(f"Total postings: {len(df)}")
    print(f"Applications marked Applied: {len(applied)}")
    print("\nDashboard preview:\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
