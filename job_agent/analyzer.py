import html
import re
import pandas as pd
from bs4 import BeautifulSoup
from app.services.skills import extract_skills

def extract_experience(description):
    """Extract years of experience mentioned in a job description."""

    description = str(description).lower()

    patterns = [
        r"\b\d+\s*(?:to|-|–)\s*\d+\s*years?\b",
        r"(?<![-\d])\d+\+?\s*years?\s+of\s+(?:relevant\s+)?experience\b",
        r"\b\d+\+?\s*years?\b",
        r"\b(?:one|two|three|four|five)\s+years?\b",
        r"\bno experience required\b",
        r"\bzero experience required\b",
        r"\bnew grad(?:uate)?s?\b",
        r"\brecent graduates?\b",
        r"\bentry[- ]level\b",
        r"\bfreshers?\b",
    ]

    matches = []

    for pattern in patterns:
        matches.extend(re.findall(pattern, description))

    # Remove shorter matches when a longer match contains them.
    cleaned_matches = []

    for match in matches:
        if not any(
            match in other and match != other
            for other in matches
        ):
            cleaned_matches.append(match)

    return list(dict.fromkeys(cleaned_matches))


def extract_education(description):
    """Extract education requirements from job descriptions."""

    description = str(description).lower()

    education_keywords = [
        "bachelor's degree",
        "bachelors degree",
        "bachelor degree",
        "master's degree",
        "masters degree",
        "master degree",
        "computer science",
        "computer engineering",
        "information technology",
        "related technical field",
        "equivalent practical experience",
        "equivalent work experience",
    ]

    found = []

    for keyword in education_keywords:
        if keyword in description:
            found.append(keyword)

    return list(dict.fromkeys(found))



def extract_section(description, heading):
    """Extract relevant content from a specific job description section."""



    soup = BeautifulSoup(
        html.unescape(str(description)),
        "html.parser"
    )

    headings = soup.find_all(
        ["h1", "h2", "h3", "h4", "strong", "b"]
    )

    target = None

    for item in headings:
        if item.get_text(" ", strip=True).lower().strip(" :") == heading.lower():
            target = item
            break

    if not target:
        return []

    results = []

    excluded_phrases = [
        "technology stack",
        "languages:",
        "frontend:",
        "database:",
        "devops & cloud:",
        "testing:",
        "what makes working",
        "compensation",
        "salary",
        "#li-remote",
    ]

    for element in target.find_all_next(
        ["h1", "h2", "h3", "h4", "li", "p"]
    ):

        # Stop when the next section heading is encountered.
        if element.name in ["h1", "h2", "h3", "h4"]:
            break

        # Sezzle uses bold text inside paragraphs as section headings.
        if element.name == "p":
            bold_heading = element.find(["strong", "b"])

            if bold_heading:
                heading_text = bold_heading.get_text(
                    " ", strip=True
                ).lower().strip(" :")

                section_headings = [
                    "about sezzle",
                    "about the role",
                    "what you'll do",
                    "what we look for",
                    "about you",
                    "what makes working at sezzle awesome",
                    "compensation",
                    "minimum requirements",
                    "preferred qualifications",
                    "who you are",
                    "responsibilities",
                ]

                if heading_text in section_headings:
                    break

        text = element.get_text(" ", strip=True)
        lower_text = text.lower()
        # Remove unrelated Stripe company-culture text.
        text = re.sub(
            r"\s*At Stripe we embrace kindness.*$",
            "",
            text,
            flags=re.IGNORECASE
        )

        lower_text = text.lower()

        if len(text) <= 20:
            continue

        if any(
        phrase in lower_text
        for phrase in excluded_phrases
        ):
            continue

        # Keep only task-oriented responsibility statements.
        if heading.lower() in [
            "responsibilities",
            "what you'll do",
            "what you will do",
            "what you'll work on",
        ]:
            action_words = [
                "develop", "build", "design", "implement",
                "maintain", "improve", "create", "write",
                "collaborate", "deliver", "debug", "deploy",
                "evaluate", "support", "document", "work",
                "ensure", "manage", "test"
            ]

            if not any(
                re.search(r"\b" + word + r"\b", lower_text)
                for word in action_words
            ):
                continue

        results.append(text)


    return list(dict.fromkeys(results))





def extract_responsibilities(description):
    """Extract meaningful responsibilities from job descriptions."""

    description = html.unescape(str(description))
    soup = BeautifulSoup(description, "html.parser")

    responsibility_headings = {
        "responsibilities",
        "key role responsibilities",
        "what you'll do",
        "what you will do",
        "what you'll work on",
        "job duties",
        "role and responsibilities",
    }

    stop_headings = {
        "who you are",
        "minimum requirements",
        "preferred qualifications",
        "preferred knowledge and skills",
        "requirements",
        "qualifications",
        "about you",
        "about us",
        "about the company",
        "about sezzle",
        "about the role",
        "interview process",
        "sezzle's technology stack",
        "technology stack",
        "languages",
        "frontend",
        "backend",
        "database",
        "devops & cloud",
        "version control",
        "ci/cd",
        "testing",
        "what makes working at sezzle awesome?",
    }


    action_words = [
        "build", "develop", "design", "implement",
        "maintain", "improve", "create", "write",
        "collaborate", "deliver", "lead", "work",
        "debug", "deploy", "support", "evaluate",
        "ensure", "manage", "test", "review",
        "optimize", "scale", "document", "contribute",
        "enhance", "leverage", "provide",
    ]

    responsibilities = []
    capture = False

    elements = soup.find_all(
        ["h1", "h2", "h3", "h4", "p", "li"]
    )

    for element in elements:
        text = element.get_text(" ", strip=True)

        if not text:
            continue

        # Detect headings represented by HTML heading tags.
        if element.name in ["h1", "h2", "h3", "h4"]:
            heading = text.lower().strip(" :")

            if heading in stop_headings:
                if capture:
                    break
                continue

            if heading in responsibility_headings:
                capture = True
                continue

        # Detect headings represented by bold text in paragraphs.
        elif element.name in ["p", "li"]:
            bold_heading = element.find(["strong", "b"])

            if bold_heading:
                heading = bold_heading.get_text(
                    " ", strip=True
                ).lower().strip(" :")

                if heading in stop_headings:
                    if capture:
                        break
                    continue

                if heading in responsibility_headings:
                    capture = True
                    continue

        if not capture:
            continue

        # Collect responsibility bullet points.
        if element.name == "li":
            if len(text) > 30:
                responsibilities.append(text)

        # Some job descriptions use paragraphs instead of bullets.
        elif element.name == "p":
            lower_text = text.lower()

            if len(text) > 30 and any(
                re.search(r"\b" + re.escape(word) + r"\b", lower_text)
                for word in action_words
            ):
                responsibilities.append(text)

        if len(responsibilities) >= 10:
            break

    # Remove duplicates while preserving the original order.
    return list(dict.fromkeys(responsibilities))[:10]



def analyze_job(job, skills):

    description = html.unescape(
        str(job.get("description", ""))
    ).lower()
    title = str(job.get("title", "")).lower()

    matched_skills = extract_skills(description, skills)

    # Define skills relevant to each job category
    skill_categories = {
        "backend": [
            "Python", "FastAPI", "Flask", "Django",
            "REST API", "Microservices",
            "PostgreSQL", "SQLAlchemy", "MySQL",
            "MongoDB", "Docker", "Pytest", "Unit Testing"
        ],

        "ai_genai": [
            "Python", "RAG", "LLM", "Generative AI",
            "Machine Learning", "Deep Learning",
            "LangChain", "LangGraph", "ChromaDB",
            "pgvector", "Vector Database"
        ],

        "software": [
            "Python", "Java", "JavaScript", "SQL",
            "Git", "Docker", "CI/CD",
            "REST API", "Unit Testing"
        ],

        "internship": [
            "Python", "Java", "JavaScript", "SQL",
            "Git", "Docker", "REST API",
            "Unit Testing", "Pytest"
        ],
    }


    # Identify the job category using title and description
    job_text = title + " " + description

    if any(word in title for word in [
    "ai engineer",
    "machine learning engineer",
    "generative ai engineer",
    "genai engineer",
    "ml engineer"
    ]):
        category = "ai_genai"

    elif "intern" in title:
        category = "internship"

    elif any(word in title for word in [
    "backend engineer",
    "backend developer",
    "backend software engineer"
    ]):
        category = "backend"

    else:
        category = "software"




    relevant_skills = skill_categories[category]

    # Normalize skill names for consistent matching
    normalized_matched = {
        skill.lower().strip()
        for skill in matched_skills
    }

    normalized_matched.update(
        skill.lower().strip()
        for skill in matched_skills
        if skill.lower().strip() == "rest apis"
    )

    # Identify matched and missing relevant skills
    relevant_matched = [
        skill for skill in relevant_skills
        if skill.lower().strip() in normalized_matched
    ]

    missing_skills = [
        skill for skill in relevant_skills
        if skill in skills
        and skill.lower().strip() not in normalized_matched
    ]

   
    return {
        "job_category": category,

        "relevant_matched_skills": ", ".join(relevant_matched),
        "relevant_missing_skills": ", ".join(missing_skills),

        "skill_coverage": round(
            len(relevant_matched) / len(relevant_skills) * 100
        ) if relevant_skills else 0,

        "required_experience": extract_experience(description),

        "required_education": extract_education(description),

        "key_responsibilities": " | ".join(
            extract_responsibilities(job.get("description", ""))
            or (
                extract_section(job.get("description", ""), "Responsibilities")
                + extract_section(job.get("description", ""), "What you'll do")
                + extract_section(job.get("description", ""), "What you will do")
                + extract_section(job.get("description", ""), "What you'll work on")
                )
        ),

        "candidate_qualities": " | ".join(
            extract_section(job.get("description", ""), "Who you are")
            + extract_section(job.get("description", ""), "About You")
        ),

        "required_qualifications": " | ".join(
            extract_section(job.get("description", ""), "Minimum requirements")
            + extract_section(job.get("description", ""), "What We Look For")
        ),

        "preferred_qualifications": " | ".join(
            extract_section(job.get("description", ""), "Preferred qualifications")
        ),
    }




def generate_analysis(
    input_file="recommended_jobs.csv",
    output_file="analyzed_jobs.csv",
    config_file="config.yaml"
):

    df = pd.read_csv(input_file).fillna("")

    with open(config_file, "r", encoding="utf-8") as file:
        import yaml
        config = yaml.safe_load(file)

    skills = config["skills"]

    analysis_results = []

    for _, row in df.iterrows():
        job = row.to_dict()

        result = analyze_job(job, skills)

        analysis_results.append(result)

    analysis_df = pd.DataFrame(analysis_results)

    final_df = pd.concat(
        [df.reset_index(drop=True), analysis_df],
        axis=1
    )

    final_df.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig"
    )

    print("\nJob Description Analysis Completed!")

    print(f"Analyzed jobs: {len(final_df)}")

    print(f"Saved report to: {output_file}")

    print("\nAnalysis Preview:")

    print(
        final_df[[
            "title",
            "company",
            "job_category",
            "relevant_matched_skills",
            "relevant_missing_skills",
            "skill_coverage",
        ]].to_string(index=False)
    )


if __name__ == "__main__":
    generate_analysis()
