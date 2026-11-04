# AI Job Search Agent: FastAPI Backend Brief

This brief is the project source of truth. Implement only one phase at a time.

## Goal

Build a small, testable Python system that fetches real jobs from supported public feeds, parses a PDF resume into a user-reviewed profile, transparently matches skills, stores jobs and application history in a database, and drafts truthful application materials. The API and any dashboard are advisory tools; nothing is submitted or sent automatically.

## Required behavior

- Never invent companies, jobs, or application URLs. Preserve the apply URL and source supplied by the source.
- Use official public APIs/feeds where available. Respect terms and `robots.txt`; do not scrape LinkedIn, Indeed, or Naukri, and never bypass logins or CAPTCHAs.
- Label matching as **Skills overlap**. It is not a hiring probability.
- `Applied` requires `confirmed_by_user: true`; otherwise return HTTP 409.
- No application-submission or message-sending endpoint.
- Draft only from an explicitly approved resume profile. Missing information must appear as `[ADD: ...]`.
- Matching and drafting require an approved profile; profile edits revoke approval.
- Keep resume PDFs in ignored `data/`, never return them from list endpoints, and do not log resume text or personal data.
- Resume parsing, matching, and drafting run locally; no external LLM integration is included.
- Do not send resume data to an external service without explicit user approval.
- Bind locally to `127.0.0.1`; restrict CORS to the configured dashboard origin.
- Routers stay thin; business logic belongs in unit-testable services.
- Add tests for changed services and endpoints. Implement the phases below in order.

## Technology and layout

Use FastAPI, Uvicorn, Pydantic v2, pydantic-settings, SQLAlchemy 2.x, SQLite, PyYAML, requests, pytest, and TestClient. Use UTC timestamps. The database URL is configurable for a future database migration.

```text
app/
  main.py, config.py, database.py, models.py, schemas.py
  routers/health.py, search.py, jobs.py, resume.py, matches.py,
    applications.py, drafts.py
  services/skills.py, filters.py, resume_parser.py, matching.py,
    job_store.py, applications.py, drafting.py
  sources/base.py, greenhouse.py, lever.py, playwright_source.py
dashboard/app.py
data/
tests/
```

Keep the existing CLI working while functionality moves into this structure.

## Data model

- `jobs`: unique indexed dedupe key; title, company, location, plain description, canonical mentioned skills, posted date, original apply URL, source, first/last seen timestamps, active flag.
- `search_runs`: start/finish timestamps, running/done/failed state, per-source result JSON, count of new jobs.
- `resume_profiles`: extracted fields and warnings as JSON text; approval/current flags and timestamps. Only one profile is current.
- `job_matches`: job/profile foreign keys, nullable skills-overlap score, matched/missing skills JSON, computed timestamp; unique per job/profile.
- `applications`: one per job, status, notes, timestamps.
- `application_events`: append-only status history, confirmation flag, note, timestamp.
- `drafts`: job, cover-letter/answer kind, optional question, body, draft/user-approved status, timestamps.

The database file and uploaded resumes must remain ignored by Git.

## API contract

Expose health/config, background search runs, job listing/detail/export, PDF resume upload/get/edit/approve, match recompute and per-job match, application create/list/update/history, and draft create/list/edit/approve endpoints. Use 201 for creates, 404 for missing records, 409 for approval/transition violations, and 413/422 for invalid uploads. Never add an endpoint that submits an application or sends a message.

### Matching

`skills_overlap = matched canonical job skills / recognized canonical job skills * 100`, rounded to one decimal. If no recognized job skills exist, return `null`. Return matched and missing skill lists. Matching requires an approved profile.

### Search

Fetch each configured source independently in a FastAPI background task. One source failure must not stop other sources; store its error in that run's results. Keep only jobs passing role, location, and entry-level filters. Upsert by dedupe key; preserve first-seen time and update last-seen time. Mark a source's jobs inactive only after a successful source fetch that did not return them.

### Applications

Allowed transitions:

| From | Allowed next statuses |
|---|---|
| Interested | Application Prepared, Applied, Rejected |
| Application Prepared | Interested, Applied, Rejected |
| Applied | Interview, Offer, Rejected |
| Interview | Offer, Rejected |
| Offer | Rejected |
| Rejected | Interested |

Every status change creates an immutable event. Moving to `Applied` requires user confirmation that they submitted on the employer's website.

### Resume and drafting

Upload PDF only, maximum 5 MB; validate extension and content type, use a generated filename outside served folders, parse into an unapproved profile, and return parser warnings. Edits revoke approval. Drafts are template-based and use only approved-profile facts; missing facts get `[ADD: ...]`. No LLM is used for drafting by default.

## Phases

A. Foundation: package structure, configuration, database/models, health route, isolated test fixtures.
B. Jobs/search: source/filter migration, deduplicating job store, search runs and job endpoints.
C. Resume: upload, retrieve, edit, approve and profile rules.
D. Matching: skills-overlap service, recompute endpoint, job match responses and filtering.
E. Applications: tracker endpoints, transitions, append-only events and confirmation.
F. Drafting: truthful template drafts, edit and approve endpoints.
G. Dashboard: Streamlit client that calls the API only.
H. Playwright: one user-selected public career page after checking terms/robots.
I. Hardening: Alembic, privacy-safe request logging, Docker, CI, and scoring documentation.

## Local development and privacy

Use `.env` for secrets and settings; `.env.example` contains placeholders only. Run the API on loopback and use the interactive `/docs` page for local testing. The dashboard must call the API and must never access the database directly. Do not commit `.env`, credentials, resume PDFs, or database files.
