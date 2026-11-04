import sys
import pandas as pd

TRACKER_FILE = "application_tracker.csv"

VALID_STATUSES = [
    "Not Reviewed",
    "Needs Verification",
    "Ready to Apply",
    "Applied",
    "Rejected",
    "Closed",
]


def main():
    if len(sys.argv) < 3:
        print(
            'Usage: python legacy/update_application.py "job title" "status"'
        )
        print("Valid statuses:", ", ".join(VALID_STATUSES))
        return

    title_query = sys.argv[1].strip().lower()
    new_status = sys.argv[2].strip()

    if new_status not in VALID_STATUSES:
        print("Invalid status.")
        print("Valid statuses:", ", ".join(VALID_STATUSES))
        return

    df = pd.read_csv(TRACKER_FILE, dtype=str).fillna("")

    matches = df["title"].astype(str).str.lower().str.contains(
        title_query,
        regex=False,
    )

    matching_rows = df[matches]

    if matching_rows.empty:
        print("No matching job found.")
        return

    if len(matching_rows) > 1:
        print("Multiple jobs matched. Please use a more specific title:")
        print(matching_rows[["title", "company", "location"]].to_string(index=True))
        return

    row_index = matching_rows.index[0]
    df.loc[row_index, "application_status"] = new_status

    if new_status == "Applied" and not df.loc[row_index, "application_date"]:
        df.loc[row_index, "application_date"] = pd.Timestamp.today().strftime(
            "%Y-%m-%d"
        )

    df.to_csv(TRACKER_FILE, index=False, encoding="utf-8-sig")

    print("\nApplication status updated successfully!")
    print("Title:", df.loc[row_index, "title"])
    print("Company:", df.loc[row_index, "company"])
    print("Location:", df.loc[row_index, "location"])
    print("New status:", new_status)


if __name__ == "__main__":
    main()