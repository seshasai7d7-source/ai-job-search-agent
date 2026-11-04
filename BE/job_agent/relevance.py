import re

from app.services.filters import clean_html


STOP_WORDS = {
    "and",
    "or",
    "with",
    "the",
    "a",
    "an",
    "for",
    "on",
    "in",
    "to",
    "of",
    "must",
    "have",
    "required",
    "preferred",
    "experience",
    "looking",
    "skills",
    "role",
    "backend",
    "engineer",
}

KEYWORD_CATALOG = [
    "Python",
    "FastAPI",
    "Flask",
    "SQL",
    "PostgreSQL",
    "RAG",
    "LLM",
    "LLMs",
    "Machine Learning",
    "AWS Lambda",
    "Kubernetes",
    "API",
    "APIs",
    "Java",
    "JavaScript",
    "Django",
    "REST API",
    "REST APIs",
]


def _normalize_text(value):
    if value is None:
        return ""
    text = str(value).lower().strip()
    text = re.sub(r"[^a-z0-9\s+/.-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _catalog_keywords(text):
    lower_text = _normalize_text(text)
    return [
        keyword
        for keyword in KEYWORD_CATALOG
        if _normalize_text(keyword) in lower_text
    ]


def extract_jd_keywords(job_description):
    description = clean_html(job_description or "")
    if not description:
        return {"required": [], "preferred": [], "keywords": []}

    preferred_split = re.split(
        r"(?i)\b(?:preferred|nice to have|bonus|optional)\b",
        description,
    )
    required_text = preferred_split[0]
    preferred_text = preferred_split[1] if len(preferred_split) > 1 else ""

    required = _catalog_keywords(required_text)
    preferred = _catalog_keywords(preferred_text)
    if not required and not preferred:
        required = _catalog_keywords(description)

    def unique_keywords(keywords):
        seen = set()
        unique = []
        for keyword in keywords:
            normalized = _normalize_text(keyword)
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique.append(keyword)
        return unique

    required = unique_keywords(required)
    preferred = unique_keywords(preferred)
    return {
        "required": required,
        "preferred": preferred,
        "keywords": required + preferred,
    }


def _keyword_matches_resume(keyword, resume_text):
    keyword_norm = _normalize_text(keyword)
    resume_norm = _normalize_text(resume_text)
    if not keyword_norm:
        return False
    if keyword_norm in resume_norm:
        return True

    tokens = {
        token for token in keyword_norm.split()
        if token not in STOP_WORDS
    }
    if not tokens:
        return False

    matched = sum(token in resume_norm for token in tokens)
    return matched >= max(1, len(tokens) // 2)


def map_keywords_to_resume(profile, keywords):
    matches = []
    for keyword in keywords:
        evidence = []
        sources = [
            profile.get("summary", ""),
            *profile.get("skills", []),
            *profile.get("projects", []),
            *profile.get("education", []),
        ]
        for item in profile.get("work_experience") or []:
            sources.extend(
                [
                    item.get("job_title", ""),
                    item.get("employer", ""),
                    *item.get("responsibilities", []),
                    *item.get("technologies", []),
                ]
            )

        seen = set()
        for source in sources:
            if _keyword_matches_resume(keyword, source):
                value = str(source)
                normalized = _normalize_text(value)
                if normalized and normalized not in seen:
                    evidence.append(value)
                    seen.add(normalized)

        matches.append(
            {
                "keyword": keyword,
                "supported": bool(evidence),
                "evidence": evidence[:3],
            }
        )

    return matches
