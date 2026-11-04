
import re
import yaml
from html import unescape
from html.parser import HTMLParser


def normalize_search_text(value):
    if value is None:
        return ""

    text = str(value).lower()
    text = re.sub(r"[\u2013\u2014\u2012\-_/]", " ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_parts = []

    def handle_data(self, data):
        self.text_parts.append(data)

    def get_text(self):
        return " ".join(self.text_parts)


def clean_html(text):
    if not text:
        return ""

    extractor = HTMLTextExtractor()
    extractor.feed(unescape(text))

    return " ".join(extractor.get_text().split())


def load_config(config_path="config.yaml"):
    with open(config_path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def is_senior_role(title):
    normalized_title = normalize_search_text(title)

    senior_keywords = [
        "senior",
        "sr",
        "staff",
        "principal",
        "lead",
        "director",
        "manager",
        "head of",
        "vice president",
        "vp",
    ]

    return any(
        normalize_search_text(keyword) in normalized_title
        for keyword in senior_keywords
    )


def matches_role(title, roles):
    normalized_title = normalize_search_text(title)

    if is_senior_role(normalized_title):
        return False

    for role in roles:
        normalized_role = normalize_search_text(role)
        if not normalized_role:
            continue

        if normalized_role in normalized_title:
            return True

        title_tokens = set(normalized_title.split())
        role_tokens = set(normalized_role.split())

        if role_tokens and role_tokens.issubset(title_tokens):
            return True

    return False



def matches_location(
    location,
    locations,
    description="",
    allow_unrestricted_remote=True,
):
    """
    Accept:
    - Any location within India.
    - International remote opportunities.

    Reject:
    - International onsite opportunities.
    """

    normalized_location = normalize_search_text(location)
    if not normalized_location:
        return False

    restricted_patterns = [
        r"\b(?:us|usa|united states)\s+only\b",
        r"\b(?:remote|fully remote|work from home)\s*[- ]\s*(?:us|usa|united states)(?:\s+only)?\b",
        r"\b(?:must be based in|based in|must be authorized to work in)\s+(?:the\s+)?(?:us|usa|united states)\b",
        r"\b(?:remote|fully remote|hybrid|work from home)\s*[- ]\s*.+\s+only\b",
        r"\b(?:remote|fully remote|work from home)\s*[-:]\s*(?:us|usa|united states|canada|uk|europe)\s*(?:only)?\b",
    ]

    if any(re.search(pattern, normalized_location) for pattern in restricted_patterns):
        return False

    india_keywords = [
        "india",
        "bengaluru",
        "bangalore",
        "hyderabad",
        "chennai",
        "pune",
        "mumbai",
        "delhi",
        "noida",
        "gurugram",
        "gurgaon",
        "kolkata",
        "ahmedabad",
        "coimbatore",
        "kochi",
        "jaipur",
    ]

    if any(keyword in normalized_location for keyword in india_keywords):
        return True

    configured_locations = [
        normalize_search_text(item)
        for item in locations
        if item
    ]
    if any(term and term in normalized_location for term in configured_locations):
        return True

    remote = any(
        term in normalized_location
        for term in ("remote", "work from home")
    )
    if remote:
        searchable = normalize_search_text(f"{location} {description}")
        return "india" in searchable or allow_unrestricted_remote

    return False


def matches_experience(text, keywords):
    text = clean_html(text).lower()

    if not text:
        return True

    if re.search(r"\b(?:no\s+experience\s+required|freshers?\s+welcome|entry[- ]level|fresher)\b", text):
        return True

    if re.search(r"\b0\s*\+\s*years?\b", text):
        return True

    preferred_patterns = [
        r"\b\d+\s*\+\s*years?\s+(?:of\s+)?experience\s+(?:is\s+)?preferred\b",
        r"\b\d+\s+years?\s+(?:of\s+)?experience\s+(?:is\s+)?preferred\b",
        r"\bpreferred\s*:\s*\d+\s*\+?\s*years?\b",
        r"\b\d+\s*\+?\s*years?\s+(?:of\s+)?experience\s+(?:is\s+)?nice\s+to\s+have\b",
        r"\b\d+\s*\+?\s*years?\s+(?:of\s+)?(?:hands\s*-?on\s+)?experience\s+(?:is\s+)?preferred\b",
    ]

    for pattern in preferred_patterns:
        text = re.sub(pattern, "", text)

    negative_patterns = [
        r"\bminimum\s+of\s+\d+\s+years?\b",
        r"\bat\s+least\s+\d+\s+years?\b",
        r"\b(?:must|need|requires?)\s+(?:to\s+)?have\s+\d+\s*\+?\s*years?\b",
        r"\b(?:must|need|requires?)\s+(?:to\s+)?have\s+\d+\s*\+?\s*years?\s+(?:of\s+)?(?:professional\s+)?experience\b",
        r"\b(?:must|need|requires?)\s+(?:at\s+least\s+)?\d+\s*\+?\s*years?\b",
        r"\b(?:must|need|requires?)\s+(?:at\s+least\s+)?\d+\s*\+?\s*years?\s+(?:of\s+)?(?:professional\s+)?experience\b",
        r"\b\d+\s*\+\s*years?\s+of\s+(?:professional\s+)?experience\b",
        r"\b\d+\s+years?\s+of\s+(?:professional\s+)?experience\s+(?:is\s+)?required\b",
        r"\b\d+\s*(?:\+\s*)?years?\s+of\s+(?:[\w-]+\s+)*experience\b",
        r"\b\d+\s*(?:\+\s*)?years?\s+(?:of\s+)?(?:[\w-]+\s+)*experience\s+(?:is\s+)?required\b",
    ]

    for pattern in negative_patterns:
        if re.search(pattern, text):
            return False

    if any(keyword.lower() in text for keyword in keywords):
        return True

    return True

def filter_jobs(jobs, config):
    legacy_mode = "search" in config
    search_config = config.get("search", config)
    roles = search_config.get("roles", [])
    locations = search_config.get("locations", [])
    experience_keywords = search_config.get("experience_keywords", [])
    filtered_jobs = []

    for job in jobs:
        title = job.get("title", "")
        location = job.get("location", "")
        description = job.get("description", "")
        combined_text = f"{title} {description}"

        if not matches_role(title, roles):
            continue

        if not matches_location(
            location,
            locations,
            description,
            allow_unrestricted_remote=legacy_mode,
        ):
            continue

        if not matches_experience(combined_text, experience_keywords):
            continue

        if not legacy_mode and not is_entry_level(job, experience_keywords):
            continue

        filtered_jobs.append(job)

    return filtered_jobs


def is_entry_level(job, keywords):
    text = normalize_search_text(
        f"{job.get('title', '')} {job.get('description', '')}"
    )
    positive_signals = [
        normalize_search_text(keyword)
        for keyword in keywords
        if keyword
    ]
    positive_signals.extend(
        (
            "no experience required",
            "freshers welcome",
            "fresher welcome",
            "entry level",
            "new grad",
            "new graduate",
            "early career",
            "0 1 years",
            "0 2 years",
            "0 years",
        )
    )
    return any(signal and signal in text for signal in positive_signals)




def calculate_skill_score(job, skills):
    """
    Calculate a weighted match score using five skill categories.
    """

    description = clean_html(
        job.get("description", "")
    ).lower()

    title = job.get("title", "").lower()
    text = title + " " + description

    categories = {
        "programming": {
            "weight": 25,
            "skills": [
                "Python", "Java", "JavaScript", "SQL"
            ],
        },
        "backend": {
            "weight": 25,
            "skills": [
                "FastAPI", "Flask", "Django",
                "REST API", "REST APIs", "Microservices"
            ],
        },
        "database": {
            "weight": 15,
            "skills": [
                "PostgreSQL", "SQLAlchemy",
                "MySQL", "MongoDB"
            ],
        },
        "ai_genai": {
            "weight": 25,
            "skills": [
                "RAG", "LLM", "Generative AI",
                "Machine Learning", "Deep Learning",
                "LangChain", "LangGraph",
                "ChromaDB", "pgvector", "Vector Database"
            ],
        },
        "testing_tools": {
            "weight": 10,
            "skills": [
                "Pytest", "Unit Testing",
                "Git", "Docker", "CI/CD"
            ],
        },
    }

    matched_skills = []
    category_scores = {}
    weighted_score = 0

    configured_skills = {skill.lower() for skill in skills}

    for category, details in categories.items():

        category_skills = [
            skill for skill in details["skills"]
            if skill.lower() in configured_skills
        ]

        if not category_skills:
            category_scores[category] = 0
            continue

        matched = []

        for skill in category_skills:

            pattern = (
                r"(?<!\w)"
                + re.escape(skill.lower())
                + r"(?!\w)"
            )

            if re.search(pattern, text):
                matched.append(skill)
                matched_skills.append(skill)

        category_score = round(
            len(matched) / len(category_skills) * 100
        )

        category_scores[category] = category_score

        weighted_score += (
            category_score * details["weight"] / 100
        )

    return {
        "skill_score": round(weighted_score),
        "matched_skills": ", ".join(matched_skills),
        "category_scores": category_scores,
    }

def detect_related_concepts(job):
    """
    Detect broader engineering concepts in job descriptions.
    These are separate from exact technology matches.
    """

    description = clean_html(
        job.get("description", "")
    ).lower()

    title = job.get("title", "").lower()
    text = title + " " + description

    concept_keywords = {
        "Backend Development": [
            "backend services",
            "backend development",
            "server-side development",
            "server side development",
            "web services",
            "application backend",
        ],
        "API Development": [
            "api development",
            "api integration",
            "web api",
            "restful services",
        ],
        "Software Engineering": [
            "software development",
            "software engineering",
            "distributed systems",
            "system design",
            "scalable applications",
        ],
        "Database Concepts": [
            "relational database",
            "database design",
            "data modeling",
            "database optimization",
        ],
        "Testing": [
            "unit tests",
            "integration tests",
            "automated testing",
            "test automation",
        ],
        "Cloud Engineering": [
            "cloud infrastructure",
            "cloud services",
            "aws",
            "azure",
            "google cloud",
        ],
    }

    detected_concepts = []

    for concept, keywords in concept_keywords.items():

        if any(keyword in text for keyword in keywords):
            detected_concepts.append(concept)

    return detected_concepts

def create_job_group(job):
    """Group similar job titles without deleting individual vacancies."""

    title = job.get("title", "").lower().strip()
    company = job.get("company", "").lower().strip()

    # Remove country names and regional labels from titles
    country_terms = [
        "argentina", "brazil", "chile", "mexico",
        "poland", "turkiye", "türkiye",
        "latam", "colombia"
    ]

    for country in country_terms:
        title = re.sub(
            r"\b" + re.escape(country) + r"\b",
            "",
            title
        )

    # Normalize spaces and punctuation
    title = re.sub(r"\([^)]*\)", "", title)
    title = re.sub(r"[^a-z0-9]+", " ", title)
    title = " ".join(title.split())

    return f"{company} - {title}"
