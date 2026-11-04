from sqlalchemy.orm import Session

from app.models import Application, ApplicationEvent


ALLOWED_NEXT = {
    "Interested": {"Application Prepared", "Applied", "Rejected"},
    "Application Prepared": {"Interested", "Applied", "Rejected"},
    "Applied": {"Interview", "Offer", "Rejected"},
    "Interview": {"Offer", "Rejected"},
    "Offer": {"Rejected"},
    "Rejected": {"Interested"},
}


class RuleViolation(ValueError):
    pass


def check_transition(
    current: str,
    new: str,
    confirmed_by_user: bool = False,
) -> None:
    if new not in ALLOWED_NEXT.get(current, set()):
        raise RuleViolation(f"Cannot move from {current} to {new}.")
    if new == "Applied" and confirmed_by_user is not True:
        raise RuleViolation(
            "Applied requires confirmed_by_user=true: confirm you submitted on the employer's website."
        )


def create_imported_application(
    db: Session,
    *,
    job_id: int,
    status: str,
    notes: str,
    confirmed_by_user: bool = False,
) -> Application:
    application = Application(
        job_id=job_id,
        status="Interested",
        notes=notes,
    )
    db.add(application)
    db.flush()

    if status != application.status:
        check_transition(application.status, status, confirmed_by_user)
        application.status = status

    db.add(
        ApplicationEvent(
            application_id=application.id,
            from_status="",
            to_status=status,
            confirmed_by_user=confirmed_by_user,
            note="Imported from legacy CSV",
        )
    )
    db.flush()
    return application
