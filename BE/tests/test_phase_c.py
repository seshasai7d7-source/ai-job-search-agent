import io

from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ResumeProfile
from app.services import resume_parser


def _pdf_bytes(text: str = "") -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    if text:
        pdf.drawString(40, 760, text)
    pdf.save()
    return buffer.getvalue()


def test_resume_upload_returns_draft_profile_and_saves_generated_pdf(
    client, monkeypatch, tmp_path
):
    monkeypatch.setattr(resume_parser, "RESUME_DIR", tmp_path)
    response = client.post(
        "/resume/upload",
        files={
            "resume": (
                "private-name.pdf",
                _pdf_bytes("Summary: Python backend engineer with FastAPI experience."),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["approved"] is False
    assert data["is_current"] is True
    assert "private-name" not in data["source_file"]
    assert (tmp_path / data["source_file"]).exists()
    assert isinstance(data["warnings"], list)
    assert client.get("/resume").json()["id"] == data["id"]


def test_resume_edit_revokes_approval_and_approve_is_explicit(
    client, monkeypatch, tmp_path
):
    monkeypatch.setattr(resume_parser, "RESUME_DIR", tmp_path)
    uploaded = client.post(
        "/resume/upload",
        files={"resume": ("resume.pdf", _pdf_bytes("Skills: Python, FastAPI"), "application/pdf")},
    )
    assert uploaded.status_code == 201

    approved = client.post("/resume/approve")
    assert approved.status_code == 200
    assert approved.json()["approved"] is True
    assert approved.json()["approved_at"] is not None

    edited = client.patch("/resume", json={"skills": ["Python"], "summary": "Reviewed summary"})
    assert edited.status_code == 200
    assert edited.json()["approved"] is False
    assert edited.json()["approved_at"] is None
    assert edited.json()["skills"] == ["Python"]
    assert edited.json()["summary"] == "Reviewed summary"


def test_uploading_new_resume_replaces_current_profile(client, monkeypatch, tmp_path):
    monkeypatch.setattr(resume_parser, "RESUME_DIR", tmp_path)
    for name in ("first.pdf", "second.pdf"):
        response = client.post(
            "/resume/upload",
            files={"resume": (name, _pdf_bytes("Skills: Python"), "application/pdf")},
        )
        assert response.status_code == 201

    with Session(client.app.state.test_engine) as db:
        profiles = db.scalars(select(ResumeProfile).order_by(ResumeProfile.id)).all()
        assert [profile.is_current for profile in profiles] == [False, True]


def test_resume_route_returns_404_without_current_profile(client):
    assert client.get("/resume").status_code == 404
    assert client.post("/resume/approve").status_code == 404
    assert client.patch("/resume", json={"skills": ["Python"]}).status_code == 404


def test_upload_validates_pdf_content_type_extension_and_signature(client):
    wrong_type = client.post(
        "/resume/upload",
        files={"resume": ("resume.pdf", _pdf_bytes(), "application/octet-stream")},
    )
    wrong_extension = client.post(
        "/resume/upload",
        files={"resume": ("resume.txt", _pdf_bytes(), "application/pdf")},
    )
    invalid_pdf = client.post(
        "/resume/upload",
        files={"resume": ("resume.pdf", b"not a pdf", "application/pdf")},
    )

    assert wrong_type.status_code == 415
    assert wrong_extension.status_code == 415
    assert invalid_pdf.status_code == 422


def test_upload_returns_warning_for_scanned_pdf(client, monkeypatch, tmp_path):
    monkeypatch.setattr(resume_parser, "RESUME_DIR", tmp_path)
    response = client.post(
        "/resume/upload",
        files={"resume": ("scan.pdf", _pdf_bytes(), "application/pdf")},
    )

    assert response.status_code == 201
    assert any("scanned" in warning for warning in response.json()["warnings"])
    assert response.json()["skills"] == []


def test_upload_rejects_file_over_configured_limit(client, monkeypatch):
    monkeypatch.setattr("app.routers.resume.settings.max_upload_mb", 0)
    response = client.post(
        "/resume/upload",
        files={
            "resume": (
                "resume.pdf",
                _pdf_bytes("Python developer"),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 413
