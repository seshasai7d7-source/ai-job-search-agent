from job_agent.relevance import extract_jd_keywords, map_keywords_to_resume


def test_extract_jd_keywords_distinguishes_required_and_preferred():
    result = extract_jd_keywords(
        """
        Requirements:
        - Python, FastAPI, SQL, and backend APIs.
        Preferred:
        - RAG, LLMs, and PostgreSQL are a plus.
        """
    )

    assert "Python" in result["required"]
    assert "FastAPI" in result["required"]
    assert "RAG" in result["preferred"]


def test_map_keywords_to_resume_returns_only_existing_profile_evidence():
    profile = {
        "summary": "Backend engineer with Python and API experience",
        "skills": ["Python", "FastAPI", "SQL"],
        "projects": ["LLM assistant using RAG"],
        "work_experience": [
            {
                "job_title": "Backend Engineer",
                "employer": "Acme",
                "responsibilities": ["Built APIs with FastAPI and PostgreSQL"],
                "technologies": ["Python", "SQL"],
            }
        ],
        "education": ["B.Tech in Computer Science"],
    }

    results = map_keywords_to_resume(profile, ["Python", "FastAPI", "Kubernetes"])

    assert results == [
        {
            "keyword": "Python",
            "supported": True,
            "evidence": [
                "Backend engineer with Python and API experience",
                "Python",
            ],
        },
        {
            "keyword": "FastAPI",
            "supported": True,
            "evidence": [
                "FastAPI",
                "Built APIs with FastAPI and PostgreSQL",
            ],
        },
        {
            "keyword": "Kubernetes",
            "supported": False,
            "evidence": [],
        },
    ]
