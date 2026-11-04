import pandas as pd


INPUT_FILE = "recommended_jobs.csv"
OUTPUT_FILE = "grouped_recommendations.csv"


def main():
    df = pd.read_csv(INPUT_FILE).fillna("")

    # Group related postings without losing their individual URLs.
    grouped = (
        df.groupby("job_group", sort=False)
        .agg(
            role=("title", "first"),
            company=("company", "first"),
            posting_count=("url", "count"),
            locations=("location", lambda values: " | ".join(dict.fromkeys(values))),
            skill_score=("skill_score", "first"),
            recommendation=("recommendation", "first"),
            experience_status=("experience_status", "first"),
            application_eligibility=(
                "application_eligibility",
                lambda values: " | ".join(dict.fromkeys(values)),
            ),
            application_urls=("url", lambda values: " | ".join(dict.fromkeys(values))),
        )
        .reset_index()
    )

    priority = {
        "Apply First": 1,
        "Verify Eligibility": 2,
        "Verify Country Restrictions": 3,
        "Review Experience Requirements": 4,
        "Manual Review": 5,
        "Not Recommended": 6,
    }

    grouped["_priority"] = grouped["recommendation"].map(priority).fillna(99)
    grouped = grouped.sort_values(
        ["_priority", "skill_score"],
        ascending=[True, False],
    ).drop(columns="_priority")

    grouped.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print(f"\nSaved grouped recommendations to {OUTPUT_FILE}")
    print(f"Original postings: {len(df)}")
    print(f"Grouped roles: {len(grouped)}")
    print("\nGrouped recommendations:")
    print(
        grouped[
            ["role", "company", "posting_count", "locations", "recommendation"]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()