from __future__ import annotations

import io
import os
import uuid

import requests
from docx import Document

BASE = "http://127.0.0.1:8000"

def expect(response: requests.Response, status: int, label: str):
    if response.status_code != status:
        raise AssertionError(f"{label}: expected {status}, got {response.status_code}: {response.text}")
    return response.json()

def docx_file() -> io.BytesIO:
    doc = Document()
    for line in (
        "Alex Morgan",
        "Python FastAPI Docker SQL communication",
        "Bachelor of Science in Computer Science, State University, 2022",
        "Software Engineer at Example Corp, 2022-2024",
        "Projects",
        "Resume Search Portal — Built a FastAPI search service.",
    ):
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

def main() -> None:
    expect(requests.get(f"{BASE}/api/health", timeout=30), 200, "health")
    email = f"advisor-live-{uuid.uuid4().hex[:10]}@example.com"
    password = "Strong123"
    expect(requests.post(f"{BASE}/api/auth/register", json={"email": email, "password": password, "full_name": "Live Advisor User"}, timeout=30), 201, "register")
    user_token = expect(requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": password}, timeout=30), 200, "user login")["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}
    admin_token = expect(requests.post(f"{BASE}/api/auth/login", json={"email": os.environ["ADMIN_EMAIL"], "password": os.environ["ADMIN_PASSWORD"]}, timeout=30), 200, "admin login")["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    resume = expect(requests.post(f"{BASE}/api/resumes/upload", headers=user_headers, files={"file": ("advisor-live.docx", docx_file(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}, timeout=60), 201, "upload")
    ai_job = expect(requests.post(f"{BASE}/api/jobs", headers=admin_headers, json={"title": "Live AI Engineer", "company": "Live Jobs", "description": "Build AI services.", "skills_required": ["Python", "Machine Learning", "Kubernetes"], "skills_preferred": ["AWS"], "experience_years": "3+ years", "education_required": "Master's degree preferred"}, timeout=30), 201, "AI job")
    data_job = expect(requests.post(f"{BASE}/api/jobs", headers=admin_headers, json={"title": "Live Data Scientist", "company": "Live Jobs", "description": "Analyze data and build models.", "skills_required": ["Python", "Pandas"]}, timeout=30), 201, "data job")

    def ask(question: str, job_id: int | None = ai_job["id"]) -> dict:
        payload = {"message": question, "resume_id": resume["id"]}
        if job_id is not None:
            payload["job_id"] = job_id
        return expect(requests.post(f"{BASE}/api/chat", headers=user_headers, json=payload, timeout=60), 200, question)

    checks = [
        ("What is the candidate's full name in the currently selected resume?", "resume", "Alex Morgan", "Live AI Engineer"),
        ("What projects are explicitly listed in the selected resume?", "resume", "Resume Search Portal", "Required skills:"),
        ("What are the main requirements of the currently selected AI Engineer job?", "job", "Kubernetes", "Alex Morgan"),
        ("Which AI Engineer requirements are explicitly supported by the resume?", "comparison", "RESUME EVIDENCE", "Top job matches:"),
        ("Which AI Engineer requirements are not supported by the resume?", "comparison", "NOT SUPPORTED", "Top job matches:"),
        ("What is Alex Morgan's current salary?", "unsupported", "outside the supported", "Live AI Engineer"),
        ("What are the top job recommendations for this resume?", "matcher", "Top job matches:", ""),
    ]
    for question, route, required, forbidden in checks:
        payload = ask(question)
        assert payload["agent_used"] == route, (question, payload)
        assert required.lower() in payload["reply"].lower(), (question, payload)
        if forbidden:
            assert forbidden.lower() not in payload["reply"].lower(), (question, payload)

    switched = ask("What are the requirements of the currently selected job?", data_job["id"])
    assert switched["agent_used"] == "job" and "Live Data Scientist" in switched["reply"]
    assert "Live AI Engineer" not in switched["reply"]
    history_ai = expect(requests.get(f"{BASE}/api/chat/history", headers=user_headers, params={"resume_id": resume["id"], "job_id": ai_job["id"]}, timeout=30), 200, "AI history")
    history_data = expect(requests.get(f"{BASE}/api/chat/history", headers=user_headers, params={"resume_id": resume["id"], "job_id": data_job["id"]}, timeout=30), 200, "Data history")
    assert history_ai and {row["job_id"] for row in history_ai} == {ai_job["id"]}
    assert history_data and {row["job_id"] for row in history_data} == {data_job["id"]}
    print("LIVE_ADVISOR_MATRIX_PASS", {"resume_id": resume["id"], "ai_job_id": ai_job["id"], "data_job_id": data_job["id"], "cases": len(checks) + 1})

if __name__ == "__main__":
    main()
