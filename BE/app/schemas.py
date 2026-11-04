from pydantic import BaseModel
from pydantic import ConfigDict, Field
from typing import Literal


class HealthResponse(BaseModel):
    status: str


class ResumeProfileEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skills: list[str] | None = None
    projects: list[str] | None = None
    education_lines: list[str] | None = None
    degrees_detected: list[str] | None = None
    experience_lines: list[str] | None = None
    experience_date_ranges: list[str] | None = None
    summary: str | None = Field(default=None, max_length=10_000)


ApplicationStatus = Literal[
    "Interested",
    "Application Prepared",
    "Applied",
    "Interview",
    "Offer",
    "Rejected",
]


class ApplicationCreate(BaseModel):
    job_id: int
    notes: str = Field(default="", max_length=10_000)


class ApplicationUpdate(BaseModel):
    status: ApplicationStatus | None = None
    confirmed_by_user: bool = False
    note: str | None = Field(default=None, max_length=10_000)


class DraftCreate(BaseModel):
    kind: Literal["cover_letter", "answer"]
    question: str | None = Field(default=None, max_length=5_000)


class DraftEdit(BaseModel):
    body: str = Field(min_length=1, max_length=30_000)
