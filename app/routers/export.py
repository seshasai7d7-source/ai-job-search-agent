import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.responses import Response

from app.database import get_db
from app.models import Job


router = APIRouter(prefix="/export", tags=["export"])

CSV_COLUMNS = (
    "title",
    "company",
    "location",
    "posted_date",
    "skills_mentioned",
    "apply_url",
    "source",
    "first_seen_at",
    "last_seen_at",
    "is_active",
)


def _safe_cell(value: object) -> str:
    if isinstance(value, datetime):
        value = value.isoformat()
    text = "" if value is None else str(value)
    if text.startswith(("=", "+", "-", "@", "\t", "\r")):
        return f"'{text}"
    return text


@router.get("/jobs.csv")
def export_jobs_csv(
    is_active: bool | None = None,
    db: Session = Depends(get_db),
) -> Response:
    statement = select(Job).order_by(Job.id)
    if is_active is not None:
        statement = statement.where(Job.is_active == is_active)
    jobs = db.scalars(statement).all()

    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(CSV_COLUMNS)
    for job in jobs:
        writer.writerow(_safe_cell(getattr(job, column)) for column in CSV_COLUMNS)

    return Response(
        content=output.getvalue().encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="jobs.csv"'},
    )
