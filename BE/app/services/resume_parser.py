import json
import re
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import ROOT_DIR, settings
from app.models import ResumeProfile
from app.services.resume_parsing import (
    ResumeParseError,
    ResumeValidationError,
    extract_candidate_profile,
    extract_resume_text,
    parse_resume_file,
)


RESUME_DIR = ROOT_DIR / "data"


def _json_text(value: list) -> str:
    return json.dumps(value, ensure_ascii=False)


def parse_and_store_resume(db: Session, content: bytes) -> ResumeProfile:
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise ValueError(f"Resume exceeds the {settings.max_upload_mb} MB size limit.")
    if not content.startswith(b"%PDF-"):
        raise ValueError("The uploaded file is not a valid PDF.")

    RESUME_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.pdf"
    resume_path = RESUME_DIR / filename
    resume_path.write_bytes(content)

    warnings = []
    try:
        text = extract_resume_text(resume_path)
        candidate = extract_candidate_profile(text).to_dict()
    except ResumeParseError as exc:
        if "No readable text was found" not in str(exc):
            resume_path.unlink(missing_ok=True)
            raise
        text = ""
        candidate = {}
        warnings.append("No selectable text found; the PDF may be scanned.")

    if text and not re.search(
        r"(?im)^\s*(summary|profile|skills|experience|education|projects)\b",
        text,
    ):
        warnings.append("No common resume section headings were detected.")
    if not candidate.get("skills"):
        warnings.append("No recognized skills were found; review the extracted profile.")

    for profile in db.scalars(
        select(ResumeProfile).where(ResumeProfile.is_current.is_(True))
    ):
        profile.is_current = False

    education = candidate.get("education", [])
    work_experience = candidate.get("work_experience", [])
    experience_lines = []
    experience_date_ranges = []
    for experience in work_experience:
        title = experience.get("job_title", "")
        employer = experience.get("employer", "")
        if title or employer:
            experience_lines.append(" at ".join(part for part in (title, employer) if part))
        for responsibility in experience.get("responsibilities", []):
            experience_lines.append(responsibility)
        start = experience.get("start_date", "")
        end = experience.get("end_date", "")
        if start or end:
            experience_date_ranges.append(f"{start} - {end}".strip(" -"))

    profile = ResumeProfile(
        source_file=filename,
        extraction_method="pypdf",
        skills=_json_text(candidate.get("skills", [])),
        skills_not_in_vocabulary="[]",
        projects=_json_text(candidate.get("projects", [])),
        education_lines=_json_text(education),
        degrees_detected=_json_text(education),
        experience_lines=_json_text(experience_lines),
        experience_date_ranges=_json_text(experience_date_ranges),
        summary=candidate.get("summary", ""),
        warnings=_json_text(warnings),
        approved=False,
        is_current=True,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile
