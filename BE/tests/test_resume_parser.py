from pathlib import Path

import pytest
from docx import Document
from reportlab.pdfgen import canvas

from app.services.resume_parser import (
    ResumeValidationError,
    extract_candidate_profile,
    parse_resume_file,
)


def _write_pdf(path, text):
    pdf = canvas.Canvas(str(path))
    pdf.setTitle("Resume")
    pdf.setFont("Helvetica", 12)
    y = 760
    for line in text.splitlines():
        pdf.drawString(50, y, line)
        y -= 18
    pdf.save()


def _write_docx(path, text):
    document = Document()
    for paragraph in text.splitlines():
        document.add_paragraph(paragraph)
    document.save(str(path))


def test_parse_resume_file_accepts_valid_pdf(tmp_path):
    resume_path = tmp_path / "resume.pdf"
    resume_text = """Python Developer at Example Corp
2022 - 2024
- Built REST APIs in Python and FastAPI.
- Worked with PostgreSQL and SQL.
Skills: Python, SQL, FastAPI, PostgreSQL
Education: B.Tech in Computer Science"""
    _write_pdf(resume_path, resume_text)

    parsed = parse_resume_file(resume_path)

    assert parsed["status"] == "parsed"
    assert parsed["file_name"] == "resume.pdf"
    assert "python" in parsed["candidate_profile"]["skills"]
    assert parsed["candidate_profile"]["work_experience"][0]["job_title"] == "Python Developer"
    assert parsed["candidate_profile"]["work_experience"][0]["employer"] == "Example Corp"


def test_parse_resume_file_accepts_valid_docx(tmp_path):
    resume_path = tmp_path / "resume.docx"
    resume_text = """Senior Software Engineer at Sample Labs
2021 - 2024
- Built backend services using Python and Flask.
- Improved data pipelines and SQL queries.
Project: AI Resume Matcher
Education: M.Tech in Artificial Intelligence"""
    _write_docx(resume_path, resume_text)

    parsed = parse_resume_file(resume_path)

    assert parsed["status"] == "parsed"
    assert parsed["candidate_profile"]["work_experience"][0]["job_title"] == "Senior Software Engineer"
    assert "flask" in parsed["candidate_profile"]["skills"]
    assert parsed["candidate_profile"]["projects"]


def test_parse_resume_file_rejects_empty_and_unsupported_files(tmp_path):
    empty_resume = tmp_path / "empty.pdf"
    empty_resume.write_bytes(b"")

    with pytest.raises(ResumeValidationError):
        parse_resume_file(empty_resume)

    unsupported = tmp_path / "resume.csv"
    unsupported.write_text("python,sql", encoding="utf-8")

    with pytest.raises(ResumeValidationError):
        parse_resume_file(unsupported)


def test_extract_candidate_profile_marks_missing_sections_unknown(tmp_path):
    resume_text = "Summary: Python developer looking for backend opportunities.\n\nSkills: Python, SQL"

    profile = extract_candidate_profile(resume_text)

    assert profile.summary.startswith("Python developer")
    assert "python" in profile.skills
    assert "work_experience" in profile.unknown_or_uncertain_fields
