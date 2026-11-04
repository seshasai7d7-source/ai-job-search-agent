import re

from app.config import load_search_config
from app.services.filters import clean_html


ALIASES = {
    "js": "JavaScript",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "rest apis": "REST API",
    "restful api": "REST API",
    "restful apis": "REST API",
    "llms": "LLM",
    "machine-learning": "Machine Learning",
    "ci cd": "CI/CD",
    "continuous integration": "CI/CD",
    "continuous delivery": "CI/CD",
}


def extract_skills(description, skills):
    description = str(description).lower()
    matched = []

    for skill in skills:
        normalized_skill = skill.lower().strip()
        if normalized_skill in ("rest api", "rest apis"):
            pattern = r"\brest\s+apis?\b"
        else:
            pattern = r"(?<!\w)" + re.escape(normalized_skill) + r"(?!\w)"

        if re.search(pattern, description):
            if normalized_skill not in [item.lower() for item in matched]:
                matched.append(skill)

    return matched


def canonical_skill(skill: str, vocabulary: list[str] | None = None) -> str | None:
    normalized = " ".join(skill.strip().lower().split())
    alias_target = ALIASES.get(normalized, skill.strip())
    allowed = vocabulary if vocabulary is not None else load_search_config().get("skills", [])
    for canonical in allowed:
        if canonical.lower() == alias_target.lower():
            return canonical
    return None


def extract_canonical_skills(text: str, vocabulary: list[str] | None = None) -> list[str]:
    allowed = vocabulary if vocabulary is not None else load_search_config().get("skills", [])
    cleaned = clean_html(text or "")
    found = []
    canonical_vocabulary = list(
        dict.fromkeys(
            canonical
            for item in allowed
            if (canonical := canonical_skill(item, allowed)) is not None
        )
    )
    for canonical in canonical_vocabulary:
        variants = [canonical]
        variants.extend(
            alias for alias, target in ALIASES.items()
            if target.lower() == canonical.lower()
        )
        variants.extend(
            item for item in allowed
            if canonical_skill(item, allowed) == canonical
        )
        if any(
            re.search(r"(?<!\w)" + re.escape(variant) + r"(?!\w)", cleaned, re.IGNORECASE)
            for variant in variants
        ) and canonical not in found:
            found.append(canonical)
    return found
