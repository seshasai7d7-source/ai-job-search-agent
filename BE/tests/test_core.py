from app.services.filters import filter_jobs


def test_filter_jobs_matches_entry_level_backend_role():
    config = {
        "search": {
            "roles": ["Python Developer", "Backend Developer"],
            "locations": ["Bengaluru", "Hyderabad", "Remote India"],
            "experience_keywords": ["fresher", "entry level", "junior"],
        }
    }

    jobs = [
        {
            "title": "Junior Backend Developer",
            "company": "Example Company",
            "location": "Bengaluru, India",
            "description": "Entry level opportunity for a Python developer.",
            "url": "https://example.com/job/1",
            "source": "Test",
        },
        {
            "title": "Senior Backend Developer",
            "company": "Example Company",
            "location": "Bengaluru, India",
            "description": "Senior role requiring extensive experience.",
            "url": "https://example.com/job/2",
            "source": "Test",
        },
    ]

    results = filter_jobs(jobs, config)

    assert len(results) == 1
    assert results[0]["title"] == "Junior Backend Developer"

def test_filter_jobs_keeps_international_remote_jobs():
    config = {
        "search": {
            "roles": ["Software Engineer"],
            "locations": ["India", "Remote India"],
            "experience_keywords": ["fresher", "junior", "graduate"],
        }
    }

    jobs = [
        {
            "title": "Junior Software Engineer",
            "company": "Example",
            "location": "Remote, Colombia",
            "description": "Junior role for Python developers.",
            "url": "https://example.com/remote",
            "source": "Test",
        }
    ]

    results = filter_jobs(jobs, config)

    assert len(results) == 1


def test_filter_jobs_rejects_mandatory_senior_experience():
    config = {
        "search": {
            "roles": ["Python Developer"],
            "locations": ["India"],
            "experience_keywords": ["fresher", "junior"],
        }
    }

    jobs = [
        {
            "title": "Junior Python Developer",
            "company": "Example",
            "location": "Bengaluru, India",
            "description": "Requires at least 5 years of professional experience.",
            "url": "https://example.com/experienced",
            "source": "Test",
        }
    ]

    results = filter_jobs(jobs, config)

    assert len(results) == 0

def test_filter_jobs_keeps_zero_plus_years_role():
    config = {
        "search": {
            "roles": ["Python Developer"],
            "locations": ["India"],
            "experience_keywords": ["fresher", "junior"],
        }
    }

    jobs = [
        {
            "title": "Junior Python Developer",
            "company": "Example",
            "location": "Bengaluru, India",
            "description": "0+ years of experience. Fresh graduates are welcome.",
            "url": "https://example.com/zero-years",
            "source": "Test",
        }
    ]

    results = filter_jobs(jobs, config)

    assert len(results) == 1


def test_filter_jobs_keeps_preferred_experience_role():
    config = {
        "search": {
            "roles": ["Python Developer"],
            "locations": ["India"],
            "experience_keywords": ["fresher", "junior"],
        }
    }

    jobs = [
        {
            "title": "Junior Python Developer",
            "company": "Example",
            "location": "Bengaluru, India",
            "description": "3 years of experience preferred, but fresh graduates may apply.",
            "url": "https://example.com/preferred",
            "source": "Test",
        }
    ]

    results = filter_jobs(jobs, config)

    assert len(results) == 1

def test_filter_jobs_rejects_international_hybrid_role():
    config = {
        "search": {
            "roles": ["Python Developer"],
            "locations": ["India", "Remote India"],
            "experience_keywords": ["fresher", "junior"],
        }
    }

    jobs = [
        {
            "title": "Junior Python Developer",
            "company": "Example",
            "location": "Hybrid - New York, USA",
            "description": "Junior Python development role.",
            "url": "https://example.com/hybrid",
            "source": "Test",
        }
    ]

    results = filter_jobs(jobs, config)

    assert len(results) == 0


def test_filter_jobs_keeps_fully_remote_international_role():
    config = {
        "search": {
            "roles": ["Python Developer"],
            "locations": ["India", "Remote India"],
            "experience_keywords": ["fresher", "junior"],
        }
    }

    jobs = [
        {
            "title": "Junior Python Developer",
            "company": "Example",
            "location": "Fully Remote",
            "description": "Junior Python development role.",
            "url": "https://example.com/fully-remote",
            "source": "Test",
        }
    ]

    results = filter_jobs(jobs, config)

    assert len(results) == 1

def test_filter_jobs_rejects_us_only_remote_role():
    config = {
        "search": {
            "roles": ["Python Developer"],
            "locations": ["India", "Remote India"],
            "experience_keywords": ["fresher", "junior"],
        }
    }

    jobs = [
        {
            "title": "Junior Python Developer",
            "company": "Example",
            "location": "Remote - US Only",
            "description": "Junior Python development role.",
            "url": "https://example.com/us-remote",
            "source": "Test",
        }
    ]

    results = filter_jobs(jobs, config)

    assert len(results) == 0

def test_filter_jobs_rejects_country_restricted_remote_roles():
    config = {
        "search": {
            "roles": ["Python Developer"],
            "locations": ["India", "Remote India"],
            "experience_keywords": ["fresher", "junior"],
        }
    }

    jobs = [
        {
            "title": "Junior Python Developer",
            "company": "Example",
            "location": "Remote - Canada Only",
            "description": "Junior Python development role.",
            "url": "https://example.com/canada",
            "source": "Test",
        },
        {
            "title": "Junior Python Developer",
            "company": "Example",
            "location": "Remote - UK Only",
            "description": "Junior Python development role.",
            "url": "https://example.com/uk",
            "source": "Test",
        },
    ]

    results = filter_jobs(jobs, config)

    assert len(results) == 0


def test_filter_jobs_matches_ai_ml_role_variants():
    config = {
        "search": {
            "roles": ["AI Engineer"],
            "locations": ["India", "Remote India"],
            "experience_keywords": ["fresher", "junior"],
        }
    }

    jobs = [
        {
            "title": "AI/ML Engineer",
            "company": "Example",
            "location": "Remote, India",
            "description": "Junior role for AI engineering work.",
            "url": "https://example.com/ai-ml",
            "source": "Test",
        }
    ]

    results = filter_jobs(jobs, config)

    assert len(results) == 1
    assert results[0]["title"] == "AI/ML Engineer"


def test_filter_jobs_rejects_must_have_years_requirement():
    config = {
        "search": {
            "roles": ["Python Developer"],
            "locations": ["India"],
            "experience_keywords": ["fresher", "junior"],
        }
    }

    jobs = [
        {
            "title": "Junior Python Developer",
            "company": "Example",
            "location": "Bengaluru, India",
            "description": "Must have 3 years of Python experience.",
            "url": "https://example.com/mandatory-years",
            "source": "Test",
        }
    ]

    results = filter_jobs(jobs, config)

    assert len(results) == 0


def test_filter_jobs_rejects_hands_on_years_requirement():
    config = {
        "search": {
            "roles": ["Python Developer"],
            "locations": ["India"],
            "experience_keywords": ["fresher", "junior"],
        }
    }

    jobs = [
        {
            "title": "Junior Python Developer",
            "company": "Example",
            "location": "Bengaluru, India",
            "description": "3+ years of hands-on Python experience required.",
            "url": "https://example.com/hands-on-years",
            "source": "Test",
        }
    ]

    results = filter_jobs(jobs, config)

    assert len(results) == 0


def test_filter_jobs_accepts_remote_worldwide_jobs():
    config = {
        "search": {
            "roles": ["Python Developer"],
            "locations": ["India", "Remote India"],
            "experience_keywords": ["fresher", "junior"],
        }
    }

    jobs = [
        {
            "title": "Junior Python Developer",
            "company": "Example",
            "location": "Remote - anywhere",
            "description": "Junior Python development role. Freshers welcome.",
            "url": "https://example.com/worldwide-remote",
            "source": "Test",
        }
    ]

    results = filter_jobs(jobs, config)

    assert len(results) == 1