from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Draft, Job, ResumeProfile
from app.schemas import DraftCreate, DraftEdit
from app.services.drafting import create_draft


router = APIRouter(tags=["drafts"])


def _draft_response(draft: Draft) -> dict:
    return {
        "id": draft.id,
        "job_id": draft.job_id,
        "kind": draft.kind,
        "question": draft.question,
        "body": draft.body,
        "status": draft.status,
        "created_at": draft.created_at,
        "updated_at": draft.updated_at,
    }


def _approved_profile(db: Session) -> ResumeProfile:
    profile = db.scalar(
        select(ResumeProfile)
        .where(
            ResumeProfile.is_current.is_(True),
            ResumeProfile.approved.is_(True),
        )
        .order_by(ResumeProfile.created_at.desc())
    )
    if profile is None:
        raise HTTPException(
            status_code=409,
            detail="An approved current resume profile is required for drafting.",
        )
    return profile


@router.post("/jobs/{job_id}/drafts", status_code=201)
def create_job_draft(
    job_id: int,
    body: DraftCreate,
    db: Session = Depends(get_db),
):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    profile = _approved_profile(db)
    try:
        draft = create_draft(body.kind, job, profile, body.question)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return _draft_response(draft)


@router.get("/jobs/{job_id}/drafts")
def list_job_drafts(job_id: int, db: Session = Depends(get_db)):
    if db.get(Job, job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    drafts = db.scalars(
        select(Draft)
        .where(Draft.job_id == job_id)
        .order_by(Draft.created_at.desc(), Draft.id.desc())
    ).all()
    return [_draft_response(draft) for draft in drafts]


@router.patch("/drafts/{draft_id}")
def edit_draft(draft_id: int, body: DraftEdit, db: Session = Depends(get_db)):
    draft = db.get(Draft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")
    if draft.status != "draft":
        raise HTTPException(status_code=409, detail="Approved drafts cannot be edited.")
    draft.body = body.body
    db.commit()
    db.refresh(draft)
    return _draft_response(draft)


@router.post("/drafts/{draft_id}/approve")
def approve_draft(draft_id: int, db: Session = Depends(get_db)):
    draft = db.get(Draft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")
    draft.status = "approved_by_user"
    db.commit()
    db.refresh(draft)
    return _draft_response(draft)
