import os

import httpx
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
APPLICATION_STATUSES = [
    "Interested",
    "Application Prepared",
    "Applied",
    "Interview",
    "Offer",
    "Rejected",
]
ALLOWED_NEXT = {
    "Interested": ["Application Prepared", "Applied", "Rejected"],
    "Application Prepared": ["Interested", "Applied", "Rejected"],
    "Applied": ["Interview", "Offer", "Rejected"],
    "Interview": ["Offer", "Rejected"],
    "Offer": ["Rejected"],
    "Rejected": ["Interested"],
}


def api_request(method: str, path: str, **kwargs):
    try:
        response = httpx.request(
            method,
            f"{API_BASE_URL}{path}",
            timeout=30,
            **kwargs,
        )
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Could not reach the local API at {API_BASE_URL}.") from exc
    if response.is_error:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise RuntimeError(f"API returned {response.status_code}: {detail}")
    return response.json() if response.content else None


def display_skills_overlap(value):
    if value is None:
        return "Not enough data"
    return f"{value:.1f}%"


def _show_error(action):
    st.error(str(action))


def _load_jobs(location, role, min_overlap):
    params = {"limit": 100}
    if location:
        params["location"] = location
    if role:
        params["role"] = role
    if min_overlap is not None:
        params["min_overlap"] = min_overlap
    return api_request("GET", "/jobs", params=params)


def _applications_by_job():
    applications = api_request("GET", "/applications")
    return {item["job_id"]: item for item in applications}


def _render_job_tracker(job, application):
    current_status = application["status"] if application else "Interested"
    selectable = [current_status] + ALLOWED_NEXT[current_status]
    chosen = st.selectbox(
        "Application status",
        selectable,
        index=0,
        key=f"status-{job['id']}",
    )
    confirmed = False
    if chosen == "Applied" and chosen != current_status:
        confirmed = st.checkbox(
            "I submitted this myself on the employer's website",
            key=f"applied-confirm-{job['id']}",
        )

    if st.button("Save status", key=f"save-status-{job['id']}"):
        try:
            if application is None:
                application = api_request(
                    "POST",
                    "/applications",
                    json={"job_id": job["id"]},
                )
                current_status = application["status"]
            if chosen != current_status:
                result = api_request(
                    "PATCH",
                    f"/applications/{application['id']}",
                    json={
                        "status": chosen,
                        "confirmed_by_user": confirmed,
                    },
                )
            st.success("Tracker updated.")
            st.rerun()
        except RuntimeError as exc:
            _show_error(exc)


def _render_jobs_tab(config):
    if st.button("Search configured job sources"):
        try:
            run = api_request("POST", "/search-runs")
            st.info(f"Search run #{run['id']} started. Refresh after it finishes.")
        except RuntimeError as exc:
            _show_error(exc)

    with st.sidebar:
        st.header("Filters")
        locations = config.get("locations", [])
        location = st.selectbox("Location", ["All"] + locations)
        role = st.text_input("Role keyword")
        min_overlap = st.slider("Minimum skills overlap", 0, 100, 0)
        use_overlap = st.checkbox("Apply minimum skills overlap", value=False)

    if st.button("Recompute skills overlap"):
        try:
            result = api_request("POST", "/matches/recompute")
            st.success(f"Computed matches for {result['computed_jobs']} jobs.")
        except RuntimeError as exc:
            _show_error(exc)

    try:
        jobs = _load_jobs(
            None if location == "All" else location,
            role.strip() or None,
            min_overlap if use_overlap else None,
        )
        applications = _applications_by_job()
    except RuntimeError as exc:
        _show_error(exc)
        return

    try:
        all_jobs = api_request("GET", "/jobs", params={"limit": 100})
        all_applications = list(applications.values())
        overlaps = [
            job["skills_overlap"]
            for job in all_jobs
            if job.get("skills_overlap") is not None
        ]
        prepared = sum(item["status"] == "Application Prepared" for item in all_applications)
        applied = sum(item["status"] == "Applied" for item in all_applications)
        average = sum(overlaps) / len(overlaps) if overlaps else None
        first, second, third, fourth = st.columns(4)
        first.metric("Jobs found", len(all_jobs))
        second.metric("Average skills overlap", display_skills_overlap(average))
        third.metric("Applications prepared", prepared)
        fourth.metric("Confirmed applied", applied)
    except RuntimeError as exc:
        _show_error(exc)

    st.caption("Skills overlap measures shared listed skills; it is not a hiring probability.")
    if not jobs:
        st.info("No jobs match the selected filters.")
        return

    for job in jobs:
        with st.container(border=True):
            st.subheader(job["title"])
            st.write(f"{job['company']} · {job['location']}")
            st.write(f"Skills overlap: **{display_skills_overlap(job.get('skills_overlap'))}**")
            left, right = st.columns(2)
            left.write("Matched skills: " + (", ".join(job.get("matched_skills", [])) or "None"))
            right.write("Missing skills: " + (", ".join(job.get("missing_skills", [])) or "None"))
            st.write(f"Posted: {job.get('posted_date') or 'Not provided'}")
            if job.get("apply_url"):
                st.markdown(f"[Open official application page]({job['apply_url']})")
            _render_job_tracker(job, applications.get(job["id"]))


def _render_resume_tab():
    try:
        profile = api_request("GET", "/resume")
    except RuntimeError as exc:
        st.info(str(exc))
        profile = None

    uploaded = st.file_uploader("Upload PDF resume", type=["pdf"])
    if uploaded is not None and st.button("Parse resume"):
        try:
            profile = api_request(
                "POST",
                "/resume/upload",
                files={"resume": (uploaded.name, uploaded.getvalue(), "application/pdf")},
            )
            st.success("Draft profile created. Review and approve it before matching or drafting.")
        except RuntimeError as exc:
            _show_error(exc)

    if profile is None:
        return
    if profile.get("warnings"):
        for warning in profile["warnings"]:
            st.warning(warning)

    with st.form("resume-profile"):
        summary = st.text_area("Summary", profile.get("summary", ""))
        skills = st.text_area("Skills (one per line)", "\n".join(profile.get("skills", [])))
        projects = st.text_area("Projects (one per line)", "\n".join(profile.get("projects", [])))
        education = st.text_area(
            "Education (one per line)",
            "\n".join(profile.get("education_lines", [])),
        )
        experience = st.text_area(
            "Experience (one per line)",
            "\n".join(profile.get("experience_lines", [])),
        )
        save = st.form_submit_button("Save profile edits")

    if save:
        try:
            profile = api_request(
                "PATCH",
                "/resume",
                json={
                    "summary": summary,
                    "skills": [line.strip() for line in skills.splitlines() if line.strip()],
                    "projects": [line.strip() for line in projects.splitlines() if line.strip()],
                    "education_lines": [
                        line.strip() for line in education.splitlines() if line.strip()
                    ],
                    "experience_lines": [
                        line.strip() for line in experience.splitlines() if line.strip()
                    ],
                },
            )
            st.success("Edits saved. The profile now requires approval again.")
        except RuntimeError as exc:
            _show_error(exc)

    if profile and not profile.get("approved"):
        if st.button("Approve reviewed profile"):
            try:
                api_request("POST", "/resume/approve")
                st.success("Resume profile approved.")
                st.rerun()
            except RuntimeError as exc:
                _show_error(exc)
    elif profile:
        st.success("Current profile approved.")


def _render_drafts_tab():
    try:
        jobs = api_request("GET", "/jobs", params={"limit": 100})
    except RuntimeError as exc:
        _show_error(exc)
        return

    if not jobs:
        st.info("Search for jobs before creating drafts.")
        return
    job_options = {f"{job['company']} — {job['title']} (#{job['id']})": job for job in jobs}
    selected_label = st.selectbox("Job", list(job_options))
    job = job_options[selected_label]
    kind = st.selectbox("Draft type", ["cover_letter", "answer"])
    question = st.text_area("Application question (for answers)")

    if st.button("Create draft"):
        try:
            created = api_request(
                "POST",
                f"/jobs/{job['id']}/drafts",
                json={"kind": kind, "question": question or None},
            )
            st.session_state["selected_draft_id"] = created["id"]
        except RuntimeError as exc:
            _show_error(exc)

    try:
        drafts = api_request("GET", f"/jobs/{job['id']}/drafts")
    except RuntimeError as exc:
        _show_error(exc)
        return

    for draft in drafts:
        st.markdown(f"**{draft['kind']} · {draft['status']} · draft #{draft['id']}**")
        edited_body = st.text_area(
            "Draft text",
            draft["body"],
            key=f"draft-body-{draft['id']}",
            height=240,
        )
        edit_col, approve_col = st.columns(2)
        if draft["status"] == "draft" and edit_col.button(
            "Save draft", key=f"edit-draft-{draft['id']}"
        ):
            try:
                api_request(
                    "PATCH",
                    f"/drafts/{draft['id']}",
                    json={"body": edited_body},
                )
                st.success("Draft updated.")
                st.rerun()
            except RuntimeError as exc:
                _show_error(exc)
        if draft["status"] == "draft" and approve_col.button(
            "Approve draft text", key=f"approve-draft-{draft['id']}"
        ):
            try:
                api_request("POST", f"/drafts/{draft['id']}/approve")
                st.success("Draft approved by you; nothing was sent.")
                st.rerun()
            except RuntimeError as exc:
                _show_error(exc)


def main():
    st.set_page_config(page_title="AI Job Search Agent", layout="wide")
    st.title("AI Job Search Agent")
    st.caption("Local dashboard connected to the FastAPI backend.")
    try:
        config = api_request("GET", "/config")
    except RuntimeError as exc:
        _show_error(exc)
        st.stop()

    jobs_tab, resume_tab, drafts_tab = st.tabs(["Jobs", "Resume profile", "Drafts"])
    with jobs_tab:
        _render_jobs_tab(config)
    with resume_tab:
        _render_resume_tab()
    with drafts_tab:
        _render_drafts_tab()


if __name__ == "__main__":
    main()
