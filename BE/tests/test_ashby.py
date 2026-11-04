import json
from pathlib import Path

from app.sources.ashby import parse_ashby_jobs


def test_parse_saved_ashby_jobs_payload():
    payload_path = Path(__file__).parent / "fixtures" / "ashby_jobs.json"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))

    jobs = parse_ashby_jobs(payload, "Ashby")

    assert jobs == [
        {
            "title": "Backend Engineer",
            "company": "Ashby",
            "location": "Remote - India",
            "description": "Build reliable services.",
            "skills_mentioned": "",
            "posted_date": "2026-10-15",
            "apply_url": "https://jobs.ashbyhq.com/ashby/example",
            "source": "",
        }
    ]
