import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

STEPS = [
    ("Fetch and filter jobs", [sys.executable, "run_search.py"]),
    ("Analyze job descriptions", [sys.executable, "-m", "job_agent.analyzer"]),
    ("Generate recommendations", [sys.executable, "-m", "job_agent.recommendations"]),
    ("Update application tracker", [sys.executable, "job_tracker.py"]),
    ("Generate grouped recommendations", [sys.executable, "group_recommendations.py"]),
    ("Generate dashboard", [sys.executable, "job_dashboard.py"]),
]


def main():
    print("=" * 60)
    print("             AI JOB SEARCH AGENT")
    print("=" * 60)

    for step_number, (step_name, command) in enumerate(STEPS, start=1):
        print(f"\n[{step_number}/{len(STEPS)}] {step_name}")
        print("-" * 60)

        result = subprocess.run(
            command,
            cwd=BASE_DIR,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            print(f"\nERROR: {step_name} failed.")
            print("The workflow has stopped to prevent later steps")
            print("from using incomplete or outdated data.")
            sys.exit(result.returncode)

        print(f"\nCompleted: {step_name}")

    print("\n" + "=" * 60)
    print("AI JOB SEARCH WORKFLOW COMPLETED")
    print("=" * 60)

    print("\nGenerated reports:")
    print("- jobs.csv")
    print("- analyzed_jobs.csv")
    print("- recommended_jobs.csv")
    print("- application_tracker.csv")
    print("- grouped_recommendations.csv")
    print("- job_dashboard.txt")


if __name__ == "__main__":
    main()