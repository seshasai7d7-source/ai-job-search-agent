
import argparse
import pandas as pd

TRACKER_FILE = "application_tracker.csv"

VALID_VALUES = [
    "Eligible",
    "Not Eligible",
    "Needs Verification",
    "Not Verified",
]

VALID_EXPERIENCE = [
    "No Experience Required",
    "Internship Accepted",
    "0-1 Years",
    "1-2 Years",
    "2-3 Years",
    "3+ Years",
    "Specific Domain Experience",
    "Needs Verification",
    "Not Verified",
]


def main():
    parser = argparse.ArgumentParser(
        description="Update job eligibility findings in the application tracker."
    )

    parser.add_argument("--title", required=True, help="Exact or partial job title")
    parser.add_argument(
        "--india", choices=VALID_VALUES, required=True,
        help="Eligibility for candidates applying from India"
    )
    parser.add_argument(
        "--fresher", choices=VALID_VALUES, required=True,
        help="Eligibility for fresh graduates"
    )
    parser.add_argument(
        "--experience",
        choices=VALID_EXPERIENCE,
        default="Needs Verification",
        help="Experience requirement stated in the official job listing"
    )
    parser.add_argument(
        "--notes", required=True,
        help="Evidence or explanation from the official job listing"
    )

    args = parser.parse_args()

    try:
        df = pd.read_csv(TRACKER_FILE, dtype=str).fillna("")
    except FileNotFoundError:
        print(f"Tracker file not found: {TRACKER_FILE}")
        return

    required_columns = [
        "title",
        "company",
        "location",
        "india_eligibility",
        "fresher_eligibility",
        "eligibility_notes",
        "application_status",
    ]

    missing_columns = [
        col for col in required_columns if col not in df.columns
    ]

    if missing_columns:
        print("Missing tracker columns:", missing_columns)
        return

    matches = df["title"].str.contains(
        args.title,
        case=False,
        regex=False,
    )

    matching_rows = df[matches]

    if matching_rows.empty:
        print("No matching job found.")
        return

    if len(matching_rows) > 1:
        print("Multiple jobs matched. Provide a more specific title:")
        print(
            matching_rows[["title", "company", "location"]].to_string(index=False)
        )
        return

    index = matching_rows.index[0]

    df.loc[index, "india_eligibility"] = args.india
    df.loc[index, "fresher_eligibility"] = args.fresher
    df.loc[index, "eligibility_notes"] = args.notes

    # Add experience requirement without overwriting existing columns.
    if "experience_requirement" not in df.columns:
        df["experience_requirement"] = "Not Verified"

    df.loc[index, "experience_requirement"] = args.experience

    # Eligibility uncertainty or rejection must never become Ready to Apply.
    if (
        args.india in ["Needs Verification", "Not Verified", "Not Eligible"]
        or args.fresher in ["Needs Verification", "Not Verified", "Not Eligible"]
        or args.experience in ["Needs Verification", "Not Verified"]
    ):
        if df.loc[index, "application_status"] != "Applied":
            df.loc[index, "application_status"] = "Needs Verification"

    df.to_csv(TRACKER_FILE, index=False, encoding="utf-8-sig")

    print("\nEligibility updated successfully!")
    print("Title:", df.loc[index, "title"])
    print("Company:", df.loc[index, "company"])
    print("Location:", df.loc[index, "location"])
    print("India eligibility:", args.india)
    print("Fresher eligibility:", args.fresher)
    print("Experience requirement:", args.experience)
    print("Evidence:", args.notes)
    print("Application status:", df.loc[index, "application_status"])


if __name__ == "__main__":
    main()
