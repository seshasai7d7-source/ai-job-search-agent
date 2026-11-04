# Legacy CSV scripts

These scripts are retained for reference and are not maintained. The FastAPI
backend replaces their job tracking, application tracking, and dashboard
workflows. The scripts read or write the old CSV files in the repository root;
they do not read or update the SQLite database.

The moved scripts are:

- `job_tracker.py`
- `update_application.py`
- `job_dashboard.py`
- `inspect_job.py`

`update_eligibility.py` and `group_recommendations.py` remain at the repository
root for now and are not part of this moved set.
