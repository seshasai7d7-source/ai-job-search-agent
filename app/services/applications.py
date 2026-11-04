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
