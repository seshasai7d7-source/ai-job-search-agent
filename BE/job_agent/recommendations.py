
import pandas as pd


def generate_recommendations(
    input_file="jobs.csv",
    output_file="recommended_jobs.csv"
):
    df = pd.read_csv(input_file).fillna("")

    def recommend(row):
        experience = str(row["experience_status"]).lower()
        eligibility = str(row["application_eligibility"]).lower()

        # Exclude roles requiring prior experience
        if "experience required" in experience:
            return "Not Recommended"

        # Prioritize fresher-friendly jobs in India
        if (
            "fresher friendly" in experience
            and "eligible - india" in eligibility
        ):
            return "Apply First"

        # International remote opportunities
        if "worldwide" in eligibility:
            return "Verify Eligibility"

        # Remote roles with country restrictions
        if "country restrictions" in eligibility:
            return "Verify Country Restrictions"

        # Junior roles with unclear experience requirements
        if "junior - verify requirements" in experience:
            return "Review Experience Requirements"

        return "Manual Review"

    df["recommendation"] = df.apply(recommend, axis=1)

    # Sort recommendations
    priority_order = {
        "Apply First": 1,
        "Verify Eligibility": 2,
        "Verify Country Restrictions": 3,
        "Review Experience Requirements": 4,
        "Manual Review": 5,
        "Not Recommended": 6,
    }

    df["sort_order"] = df["recommendation"].map(priority_order)

    df = df.sort_values(
        by=["sort_order", "skill_score"],
        ascending=[True, False]
    )

    df = df.drop(columns=["sort_order"])

    df.to_csv(output_file, index=False, encoding="utf-8-sig")

    print("\nRecommendation Summary:")
    print(df["recommendation"].value_counts().to_string())

    print(f"\nSaved recommendations to {output_file}")

    print("\nRecommended Jobs:")
    print(
        df[[
            "title",
            "company",
            "location",
            "skill_score",
            "experience_status",
            "application_eligibility",
            "recommendation",
            "url"
        ]].to_string(index=False)
    )


if __name__ == "__main__":
    generate_recommendations()
