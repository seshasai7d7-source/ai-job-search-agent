import csv
import io

import pytest
from sqlalchemy.orm import Session

from app.models import Job
from app.routers.export import CSV_COLUMNS


def _job(dedupe_key: str, **overrides) -> Job:
    values = {
        "dedupe_key": dedupe_key,
        "title": "Python Developer",
        "company": "Acme",
        "location": "Bengaluru",
        "description": "Private description omitted from the export.",
        "posted_date": "2026-01-02",
        "skills_mentioned": "Python, FastAPI",
        "apply_url": "https://example.com/job",
        "source": "greenhouse:acme",
        "is_active": True,
    }
    values.update(overrides)
    return Job(**values)


def _rows(response):
    return list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))


def test_export_has_utf8_bom_attachment_and_header_only_for_empty_database(client):
    response = client.get("/export/jobs.csv")

    assert response.status_code == 200
    assert response.content.startswith(b"\xef\xbb\xbf")
    assert "attachment" in response.headers["content-disposition"].lower()
    assert "jobs.csv" in response.headers["content-disposition"]
    assert _rows(response) == [list(CSV_COLUMNS)]


def test_export_includes_only_expected_columns(client):
    with Session(client.app.state.test_engine) as db:
        db.add(_job("job-1"))
        db.commit()

    rows = _rows(client.get("/export/jobs.csv"))

    assert rows[0] == list(CSV_COLUMNS)
    assert len(rows[1]) == len(CSV_COLUMNS)
    assert "Private description" not in "\n".join(",".join(row) for row in rows)


def test_export_optional_is_active_filter(client):
    with Session(client.app.state.test_engine) as db:
        db.add_all(
            [
                _job("active"),
                _job("inactive", is_active=False),
            ]
        )
        db.commit()

    all_rows = _rows(client.get("/export/jobs.csv"))
    active_rows = _rows(client.get("/export/jobs.csv?is_active=true"))
    inactive_rows = _rows(client.get("/export/jobs.csv?is_active=false"))

    assert len(all_rows) == 3
    assert [row[-1] for row in active_rows[1:]] == ["True"]
    assert [row[-1] for row in inactive_rows[1:]] == ["False"]


@pytest.mark.parametrize(
    "title",
    [
        "=SUM(1,2)",
        "+SUM(1,2)",
        "-1+2",
        "@SUM(1,2)",
        "\t=SUM(1,2)",
        "\r=SUM(1,2)",
    ],
)
def test_export_neutralizes_formula_prefixes(client, title):
    with Session(client.app.state.test_engine) as db:
        db.add(_job(f"job-{ord(title[0])}", title=title))
        db.commit()

    rows = _rows(client.get("/export/jobs.csv"))

    assert rows[1][0] == f"'{title}"
