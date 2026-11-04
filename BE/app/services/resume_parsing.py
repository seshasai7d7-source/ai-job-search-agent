import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from pypdf import PdfReader

from app.services.filters import load_config
from app.services.resume_models import CandidateProfile, WorkExperience
from app.services.skills import extract_skills


MAX_RESUME_SIZE_BYTES = 5 * 1024 * 1024
SUPPORTED_RESUME_EXTENSIONS = {".pdf", ".docx", ".txt"}


class ResumeValidationError(ValueError):
    pass


class ResumeParseError(ValueError):
    pass


def validate_resume_file(file_path, max_size_bytes=MAX_RESUME_SIZE_BYTES):
    path = Path(file_path)

    if not path.exists():
        raise ResumeValidationError("Resume file does not exist.")

    if not path.is_file():
        raise ResumeValidationError("Resume path is not a file.")

    if path.suffix.lower() not in SUPPORTED_RESUME_EXTENSIONS:
        raise ResumeValidationError(
            "Unsupported file type. Please upload a PDF, DOCX, or TXT resume."
        )

    file_size = path.stat().st_size
    if file_size == 0:
        raise ResumeValidationError("Resume file is empty.")

    if file_size > max_size_bytes:
        raise ResumeValidationError(
            f"Resume file is too large. Maximum allowed size is {max_size_bytes} bytes."
        )

    return path


def normalize_resume_text(text):
    if not text:
        return ""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace("\xa0", " ")
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    normalized = re.sub(r"[ \t]+\n", "\n", normalized)
    normalized = re.sub(r"\n[ \t]+", "\n", normalized)
    normalized = re.sub(r" +", " ", normalized)
    return normalized.strip()


def extract_text_from_pdf(file_path):
    try:
        reader = PdfReader(str(file_path))
        pages = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages.append(page_text)

        if not pages:
            raise ResumeParseError("No readable text was found in the PDF file.")

        return normalize_resume_text("\n\n".join(pages))
    except Exception as exc:  # pragma: no cover - exercised through test file creation
        raise ResumeParseError(f"Could not read PDF resume: {exc}") from exc


def extract_text_from_docx(file_path):
    try:
        with zipfile.ZipFile(file_path) as archive:
            if "word/document.xml" not in archive.namelist():
                raise ResumeParseError("DOCX document.xml was not found.")

            root = ET.fromstring(archive.read("word/document.xml"))
            namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            paragraphs = [
                node.text
                for node in root.findall(".//w:t", namespace)
                if node.text and node.text.strip()
            ]

        if not paragraphs:
            raise ResumeParseError("No readable text was found in the DOCX file.")

        return normalize_resume_text("\n".join(paragraphs))
    except Exception as exc:  # pragma: no cover - exercised through real DOCX creation
        raise ResumeParseError(f"Could not read DOCX resume: {exc}") from exc


def extract_text_from_txt(file_path):
    try:
        raw = file_path.read_bytes()
        for encoding in ("utf-8-sig", "utf-16", "cp1252", "latin-1"):
            try:
                text = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ResumeParseError("Text resume could not be decoded.")

        normalized = normalize_resume_text(text)
        if not normalized:
            raise ResumeParseError("Text resume is empty or contains no readable content.")
        return normalized
    except Exception as exc:
        raise ResumeParseError(f"Could not read TXT resume: {exc}") from exc


def extract_resume_text(file_path):
    path = validate_resume_file(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return extract_text_from_pdf(path)
    if suffix == ".docx":
        return extract_text_from_docx(path)
    if suffix == ".txt":
        return extract_text_from_txt(path)

    raise ResumeValidationError("Unsupported resume format.")


def _candidate_skills(text):
    config = load_config()
    detected = [skill.lower() for skill in extract_skills(text, config.get("skills", []))]
    lower_text = text.lower()
    return sorted(dict.fromkeys(detected), key=lambda value: lower_text.index(value))


def _extract_summary(text):
    patterns = [
        r"(?i)summary[:\-]?\s*(.*?)(?:\n\n|\n[A-Z][A-Za-z ]{2,}[:\-]|$)",
        r"(?i)profile[:\-]?\s*(.*?)(?:\n\n|\n[A-Z][A-Za-z ]{2,}[:\-]|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.DOTALL)
        if match:
            candidate = re.sub(r"\s+", " ", match.group(1)).strip()
            if len(candidate) > 25:
                return candidate[:500]

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines[:10]:
        if len(line) > 30 and not re.search(r"\b(?:phone|email|linkedin|github)\b", line.lower()):
            return line[:500]

    return ""


def _extract_work_experience(text):
    entries = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    i = 0

    while i < len(lines):
        line = lines[i]
        lower_line = line.lower()

        if re.search(r"\b(?:developer|engineer|analyst|intern|consultant|scientist|manager|designer)\b", lower_line):
            experience = WorkExperience()
            title_text = line

            if " at " in lower_line:
                title, employer = re.split(r"\s+at\s+", line, flags=re.IGNORECASE, maxsplit=1)
                experience.job_title = title.strip(" -|")
                experience.employer = employer.strip(" -|")
            elif " | " in line:
                parts = [part.strip() for part in line.split("|")]
                if len(parts) >= 2:
                    experience.job_title = parts[0].strip(" -|")
                    experience.employer = parts[1].strip(" -|")
            else:
                experience.job_title = title_text.strip(" -|")
                experience.employer = "Unknown"

            if re.search(r"\b(?:intern|internship)\b", lower_line):
                experience.employment_type = "Internship"

            j = i + 1
            responsibilities = []
            technologies = []
            while j < len(lines):
                next_line = lines[j]
                next_lower = next_line.lower()

                if re.search(r"\b(?:summary|skills|education|projects|certifications|achievements)\b", next_lower):
                    break
                if re.search(r"\b(?:developer|engineer|analyst|intern|consultant|scientist|manager|designer)\b", next_lower):
                    break
                if next_line.startswith("http"):
                    break

                if next_line.startswith("-") or next_line.startswith("•") or next_line.startswith("*"):
                    cleaned = re.sub(r"^[\-•*]+\s*", "", next_line).strip()
                    responsibilities.append(cleaned)
                elif re.search(r"\d{4}|present|current|internship|full[- ]time|contract|part[- ]time", next_lower):
                    if not experience.start_date and re.search(r"\d{4}", next_lower):
                        experience.start_date = next_line
                    elif not experience.end_date and re.search(r"(present|current|\d{4})", next_lower):
                        experience.end_date = next_line
                elif len(next_line) > 2:
                    responsibilities.append(next_line)
                j += 1

            experience.responsibilities = [item for item in responsibilities if item][:8]
            experience.technologies = _candidate_skills("\n".join(experience.responsibilities))

            has_employer_context = experience.employer not in ("", "Unknown")
            has_temporal_context = bool(
                experience.start_date or experience.end_date or re.search(r"\b(?:present|current|internship|full[- ]time|part[- ]time|\d{4})\b", line.lower())
            )

            if has_employer_context or has_temporal_context or experience.responsibilities:
                entries.append(experience)
            i = j
            continue

        i += 1

    return entries


def _extract_education(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    matches = []
    for line in lines:
        lower_line = line.lower()
        if re.search(r"\b(?:b\.tech|btech|b\.e|be|bachelor|master|m\.tech|msc|mca|phd|computer science|information technology)\b", lower_line):
            matches.append(line)
    return matches[:5]


def _extract_projects(text):
    projects = []
    for block in re.split(r"\n\s*\n", text):
        if re.search(r"\bproject\b|\bportfolio\b|\bimplementation\b", block.lower()):
            cleaned = re.sub(r"\s+", " ", block).strip()
            if len(cleaned) > 20:
                projects.append(cleaned)
    return projects[:5]


def _extract_certifications(text):
    certifications = []
    for line in text.splitlines():
        lower = line.lower()
        if re.search(r"\b(?:certified|certificate|aws|azure|google|oracle|scrum|pmp)\b", lower):
            certifications.append(line.strip())
    return certifications[:5]


def _extract_achievements(text):
    achievements = []
    for line in text.splitlines():
        lower = line.lower()
        if re.search(r"\b(?:awarded|won|ranked|achievement|recognized|award|top|best)\b", lower):
            achievements.append(line.strip())
    return achievements[:5]


def extract_candidate_profile(text):
    cleaned = normalize_resume_text(text)
    if not cleaned:
        raise ResumeParseError("Resume text is empty.")

    skills = _candidate_skills(cleaned)
    work_experience = _extract_work_experience(cleaned)
    profile = CandidateProfile(
        summary=_extract_summary(cleaned),
        skills=skills,
        work_experience=work_experience,
        education=_extract_education(cleaned),
        projects=_extract_projects(cleaned),
        certifications=_extract_certifications(cleaned),
        achievements=_extract_achievements(cleaned),
    )

    unknown_fields = []
    if not profile.summary:
        unknown_fields.append("summary")
    if not profile.skills:
        unknown_fields.append("skills")
    if not profile.work_experience:
        unknown_fields.append("work_experience")

    if unknown_fields:
        profile.unknown_or_uncertain_fields.extend(unknown_fields)

    return profile


def parse_resume_file(file_path):
    text = extract_resume_text(file_path)
    profile = extract_candidate_profile(text)

    return {
        "file_name": Path(file_path).name,
        "text": text,
        "candidate_profile": profile.to_dict(),
        "status": "parsed" if profile.summary or profile.work_experience or profile.skills else "incomplete",
    }
