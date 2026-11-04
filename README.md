# AI Job Search Agent

![CI](https://github.com/seshasai7d7-source/ai-job-search-agent/actions/workflows/ci.yml/badge.svg)

An AI job discovery, filtering, skills-matching, and application-tracking system built with Python. It collects public job listings, evaluates opportunities against a reviewed candidate profile, and provides a dashboard for managing the job search.

## Features

- Collects public job listings from Greenhouse, Lever, and Ashby job boards.
- Filters opportunities by target job roles, location, and experience preferences.
- Calculates technical skill-match scores.
- Analyzes job descriptions using Python-based matching.
- Groups similar job postings.
- Tracks application status, experience requirements, and location eligibility.
- Generates a job-search dashboard with recommendations and follow-ups.
- Exports results and reports to CSV and text files.
- Keeps application decisions under the user's control; no automatic applications are submitted.

## Target Roles

- Python Developer
- Backend Developer
- Junior Software Engineer
- AI Engineer
- Generative AI Engineer
- Machine Learning Engineer

## Technology Stack

- Python
- Pandas
- FastAPI REST API
- Uvicorn ASGI server
- Next.js, React, and TypeScript frontend
- SQLAlchemy 2.x and SQLite
- Pydantic Settings
- Python Dotenv
- BeautifulSoup
- Requests
- Greenhouse Job Board API
- Lever Postings API
- Ashby Job Board API
- PyYAML
- SQLite persistence in the new API; CSV persistence remains in legacy CLI workflows during migration
- Pytest

## Project Structure

```text
ai-job-search-agent/
├── FE/                 # Next.js web application
├── BE/                 # FastAPI API, Python CLI, migrations, and tests
├── docs/               # Shared project documentation
├── .github/            # Repository workflows
├── .gitignore
└── README.md
```

The old CSV scripts in `BE/legacy/` are not maintained and are replaced by the API. They read or write CSV files and do not update the SQLite database. The legacy `BE/job_agent` modules remain available during migration; their filters, skill extraction, and resume parser delegate to implementations under `BE/app/services/`.

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/seshasai7d7-source/ai-job-search-agent.git
cd ai-job-search-agent
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate the environment

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```bash
cd BE
pip install -r requirements.txt
```

## Configuration

From `BE/`, update `config.yaml` with:

- Companies and their Greenhouse or Lever board identifiers.
- Target job titles.
- Preferred locations.
- Technical skills.
- Experience-level preferences.

## Run the Agent

Run the complete workflow:

```bash
cd BE
python run_agent.py
```

The workflow performs:

1. Public job collection and filtering.
2. Job-description analysis.
3. Recommendation generation.
4. Application tracker updates.
5. Grouped recommendation generation.
6. Dashboard generation.

## Run the FastAPI Backend

Start the FastAPI backend from `BE/`:

```bash
cd BE
uvicorn app.main:app --reload --host 127.0.0.1
```

Open `http://127.0.0.1:8000/docs` for the interactive API reference. The API is implemented phase-by-phase from [docs/PROJECT_BRIEF.md](docs/PROJECT_BRIEF.md). The old CSV CLI workflow remains available through `BE/run_agent.py`, but it is not maintained. Use the API as the supported workflow; legacy scripts read or write CSV files and do not update the SQLite database.

Export stored jobs with `GET /export/jobs.csv`. The download includes UTF-8 BOM encoding and spreadsheet-formula-safe cells; the optional `is_active` query parameter filters active or inactive jobs.

The SQLite database defaults to `BE/data/job_agent.db`. Configure `DATABASE_URL`, `MAX_UPLOAD_MB`, or `ALLOWED_ORIGIN` in `BE/.env` as needed; use `BE/.env.example` as a reference. Database and resume files are git-ignored.

Initialize or update the API database before starting the backend:

```bash
cd BE
alembic upgrade head
```

The API logs only the HTTP method, URL path (without query parameters), response status, and duration. It does not log request or response bodies.

Run the Streamlit API client separately:

```bash
cd BE
streamlit run dashboard/app.py
```

The dashboard calls the API at `http://127.0.0.1:8000` by default. It never reads the database directly. Set `API_BASE_URL` only when intentionally changing the API endpoint.

## Additional Commands

The Next.js frontend is in `FE/`. Start the backend as described above, then open a separate terminal:

```powershell
cd FE
npm ci
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Frontend checks are `npm run lint`, `npm test`, and `npm run build`.

Import the legacy jobs and application tracker CSVs into the database. Start with a dry run; a real run creates a timestamped database backup before writing:

```bash
cd BE
python scripts/import_csv_to_db.py --jobs-csv jobs.csv --applications-csv application_tracker.csv --dry-run
```

After checking the counts, remove `--dry-run` to import. Legacy `Applied` rows are downgraded to `Application Prepared` unless `--confirm-legacy-applied` is supplied.

Legacy CSV application status update (not maintained; use the API instead):

```bash
cd BE
python legacy/update_application.py "job title" "status"
```

Update eligibility information:

```bash
cd BE
python update_eligibility.py
```

Generate the legacy CSV dashboard (not maintained; use the Streamlit API client instead):

```bash
cd BE
python legacy/job_dashboard.py
```

Run tests:

```bash
cd BE
pytest
```

## Skills-overlap score

The FastAPI API reports `skills_overlap` as the percentage of unique, recognized canonical skills mentioned in a job description that also appear in the approved profile. The value is rounded to one decimal place; it is `null` when the job description contains no recognized skills. This is a skills comparison only, not a hiring probability or a prediction of interview or offer outcomes.

## Docker

Build and run the API locally with a persistent database volume:

```bash
docker build -t ai-job-search-agent ./BE
docker run --rm -p 127.0.0.1:8000:8000 -v job-agent-data:/app/data ai-job-search-agent
```

The container applies Alembic migrations before starting Uvicorn. It runs as a non-root user, checks `/health`, and stores SQLite data under the mounted `/app/data` volume. The build context excludes local CSVs, databases, PDFs, tests, and environment files. Configure optional settings with environment variables; do not copy `.env` or resume files into the image.

## Output Files

| File | Description |
|---|---|
| `jobs.csv` | Collected and filtered job listings |
| `analyzed_jobs.csv` | Technical skill analysis |
| `recommended_jobs.csv` | Job recommendations |
| `application_tracker.csv` | Application and eligibility tracking |
| `grouped_recommendations.csv` | Similar job postings grouped together |
| `job_dashboard.txt` | Job-search dashboard report |

Generated reports and personal tracking data are excluded from version control.

## Important Notes

- Skills-overlap values are advisory comparisons, not hiring predictions.
- A high technical match does not guarantee interview selection.
- Remote job listings do not automatically permit applicants to work from India.
- Verify country restrictions, work authorization, experience requirements, and eligibility on the employer's official careers page.
- The project does not automatically submit job applications.
- Application decisions and status updates remain under the user's control.
- Never commit API keys, `.env` files, or personal application-tracking data.

## Future Improvements

- Add more public job-board integrations.
- Improve matching with semantic similarity and embeddings.
- Add alerts for newly discovered jobs.
- Improve the frontend and expand its automated test coverage.
- Expand automated test coverage.
- Add continuous integration.

## Author

**Sesha Sai Kolla**

Computer Science and Engineering — Artificial Intelligence
