import json

from app.models import Draft, Job, ResumeProfile
from app.services.matching import calculate_skills_overlap
from app.services.skills import extract_canonical_skills


def build_draft_body(
    kind: str,
    job: Job,
    profile: ResumeProfile,
    question: str | None = None,
) -> str:
    if kind not in {"cover_letter", "answer"}:
        raise ValueError("Draft kind must be cover_letter or answer.")

    skills = json.loads(profile.skills)
    projects = json.loads(profile.projects)
    education = json.loads(profile.education_lines)
    experience = json.loads(profile.experience_lines)
    job_skills = extract_canonical_skills(job.description)
    _, matched_skills, _ = calculate_skills_overlap(job_skills, skills)

    skill_text = ", ".join(matched_skills[:5]) or "[ADD: relevant skills from your approved profile]"
    project_text = projects[0] if projects else "[ADD: a relevant project from your experience]"
    education_text = education[0] if education else "[ADD: your relevant education]"
    summary_text = profile.summary or "[ADD: a short summary of your relevant background]"

    if kind == "cover_letter":
        return (
            f"Dear Hiring Team,\n\n"
            f"I am interested in the {job.title or '[ADD: job title]'} role at "
            f"{job.company or '[ADD: company name]'}. My approved profile includes "
            f"experience with {skill_text}.\n\n"
            f"Relevant project: {project_text}\n\n"
            f"Education: {education_text}\n\n"
            f"{summary_text}\n\n"
            f"Sincerely,\n[ADD: Your name]"
        )

    prompt = question.strip() if question else "[ADD: the application question]"
    experience_text = "; ".join(experience[:3]) or "[ADD: relevant experience]"
    return (
        f"Question: {prompt}\n\n"
        f"Draft answer: {summary_text} My relevant skills include {skill_text}. "
        f"Relevant experience: {experience_text}. "
        f"Relevant project: {project_text}. "
        f"Education: {education_text}."
    )


def create_draft(
    kind: str,
    job: Job,
    profile: ResumeProfile,
    question: str | None = None,
) -> Draft:
    if not profile.approved or not profile.is_current:
        raise ValueError("An approved current resume profile is required for drafting.")
    if kind == "answer" and not question:
        raise ValueError("An application question is required for an answer draft.")
    return Draft(
        job_id=job.id,
        kind=kind,
        question=question,
        body=build_draft_body(kind, job, profile, question),
        status="draft",
    )
