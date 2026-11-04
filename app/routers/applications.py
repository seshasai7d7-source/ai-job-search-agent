from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Application, ApplicationEvent, Job
from app.schemas import ApplicationCreate, ApplicationUpdate
from app.services.applications import RuleViolation, check_transition


router = APIRouter(prefix="/applications", tags=["applications"])


def _application_response(application: Application, job: Job) -> dict:
    return {
        "id": application.id,
        "job_id": application.job_id,
        "status": application.status,
        "notes": application.notes,
        "created_at": application.created_at,
        "updated_at": application.updated_at,
        "job": {
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "apply_url": job.apply_url,
            "source": job.source,
        },
    }


@router.post("", status_code=201)
def create_application(body: ApplicationCreate, db: Session = Depends(get_db)):
    job = db.get(Job, body.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    application = Application(job_id=job.id, status="Interested", notes=body.notes)
    db.add(application)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="An application tracker entry already exists for this job.",
        ) from exc
    db.refresh(application)
    return _application_response(application, job)


@router.get("")
def list_applications(
    status: str | None = None,
    db: Session = Depends(get_db),
):
    statement = select(Application, Job).join(Job, Application.job_id == Job.id)
    if status is not None:
        statement = statement.where(Application.status == status)
    return [
        _application_response(application, job)
        for application, job in db.execute(
            statement.order_by(Application.updated_at.desc())
        )
    ]


@router.patch("/{application_id}")
def update_application(
    application_id: int,
    body: ApplicationUpdate,
    db: Session = Depends(get_db),
):
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found.")

    note = body.note or ""
    if body.status and body.status != application.status:
        from_status = application.status
        try:
            check_transition(from_status, body.status, body.confirmed_by_user)
        except RuleViolation as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        event = ApplicationEvent(
            application_id=application.id,
            from_status=from_status,
            to_status=body.status,
            confirmed_by_user=body.confirmed_by_user,
            note=note,
        )
        db.add(event)
        application.status = body.status
    if body.note is not None:
        application.notes = body.note
    application.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(application)
    job = db.get(Job, application.job_id)
    return _application_response(application, job)


@router.get("/{application_id}/events")
def get_application_events(application_id: int, db: Session = Depends(get_db)):
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found.")
    events = db.scalars(
        select(ApplicationEvent)
        .where(ApplicationEvent.application_id == application_id)
        .order_by(ApplicationEvent.created_at, ApplicationEvent.id)
    ).all()
    return [
        {
            "id": event.id,
            "from_status": event.from_status,
            "to_status": event.to_status,
            "confirmed_by_user": event.confirmed_by_user,
            "note": event.note,
            "created_at": event.created_at,
        }
        for event in events
    ]
