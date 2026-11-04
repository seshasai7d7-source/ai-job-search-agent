from dataclasses import dataclass, field


@dataclass
class WorkExperience:
    employer: str = ""
    job_title: str = ""
    employment_type: str = ""
    start_date: str = ""
    end_date: str = ""
    responsibilities: list[str] = field(default_factory=list)
    technologies: list[str] = field(default_factory=list)


@dataclass
class CandidateProfile:
    summary: str = ""
    skills: list[str] = field(default_factory=list)
    work_experience: list[WorkExperience] = field(default_factory=list)
    education: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    achievements: list[str] = field(default_factory=list)
    unknown_or_uncertain_fields: list[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "summary": self.summary,
            "skills": self.skills,
            "work_experience": [
                {
                    "employer": item.employer,
                    "job_title": item.job_title,
                    "employment_type": item.employment_type,
                    "start_date": item.start_date,
                    "end_date": item.end_date,
                    "responsibilities": item.responsibilities,
                    "technologies": item.technologies,
                }
                for item in self.work_experience
            ],
            "education": self.education,
            "projects": self.projects,
            "certifications": self.certifications,
            "achievements": self.achievements,
            "unknown_or_uncertain_fields": self.unknown_or_uncertain_fields,
        }
