from __future__ import annotations

import io
import os
import uuid

import requests
from docx import Document

BASE = os.getenv("BASE_URL", "http://127.0.0.1:8000")
ADMIN_EMAIL = os.environ["ADMIN_EMAIL"]
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]

def check(response: requests.Response, status: int, label: str):
    if response.status_code != status:
        raise AssertionError(f"{label}: expected {status}, got {response.status_code}: {response.text}")
    return response.json() if response.content else None

def resume_file(name: str, lines: list[str]) -> tuple[str, io.BytesIO, str]:
    doc = Document()
    for line in lines:
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return name, buf, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

def main() -> None:
    check(requests.get(f"{BASE}/api/health", timeout=30), 200, "health")
    suffix = uuid.uuid4().hex[:10]
    users = []
    for label in ("a", "b"):
        email = f"audit-{label}-{suffix}@example.com"
        check(requests.post(f"{BASE}/api/auth/register", json={"email": email, "password": "Strong123", "full_name": f"Audit User {label.upper()}"}, timeout=30), 201, f"register {label}")
        token = check(requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": "Strong123"}, timeout=30), 200, f"login {label}")["access_token"]
        users.append((email, token))
    user_a, user_b = users
    ha = {"Authorization": f"Bearer {user_a[1]}"}
    hb = {"Authorization": f"Bearer {user_b[1]}"}
    admin_token = check(requests.post(f"{BASE}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30), 200, "admin login")["access_token"]
    hadmin = {"Authorization": f"Bearer {admin_token}"}

    denied = requests.post(f"{BASE}/api/jobs", headers=ha, json={"title": "Should Be Denied", "description": "No privilege", "skills_required": []}, timeout=30)
    check(denied, 403, "non-admin create job")
    resume = check(requests.post(f"{BASE}/api/resumes/upload", headers=ha, files={"file": resume_file("audit.docx", ["Audit Candidate", "Python FastAPI", "Bachelor of Science, 2022", "Engineer at Example, 2022-2024", "Projects", "Audit Portal"])}, timeout=60), 201, "resume upload")
    cross_resume = requests.get(f"{BASE}/api/resumes/{resume['id']}", headers=hb, timeout=30)
    check(cross_resume, 404, "cross-user resume access")
    invalid_id = requests.get(f"{BASE}/api/resumes/999999999", headers=ha, timeout=30)
    check(invalid_id, 404, "missing resume")
    invalid_upload = requests.post(f"{BASE}/api/resumes/upload", headers=ha, files={"file": ("audit.txt", io.BytesIO(b"not supported"), "text/plain")}, timeout=30)
    check(invalid_upload, 422, "unsupported upload")
    assert "Traceback" not in invalid_upload.text and "Exception" not in invalid_upload.text

    job = check(requests.post(f"{BASE}/api/jobs", headers=hadmin, json={"title": f"Audit Job {suffix}", "company": "Audit Co", "location": "Remote", "description": "Build Python services.", "skills_required": ["Python"], "skills_preferred": ["Kubernetes"]}, timeout=30), 201, "admin create job")
    search = check(requests.get(f"{BASE}/api/jobs/search", headers=ha, params={"skill": "kubernetes"}, timeout=30), 200, "preferred skill search")
    assert any(row["id"] == job["id"] for row in search)
    updated = check(requests.put(f"{BASE}/api/jobs/{job['id']}", headers=hadmin, json={"title": f"Updated Audit Job {suffix}"}, timeout=30), 200, "admin update job")
    assert updated["title"] == f"Updated Audit Job {suffix}"
    stale = requests.put(f"{BASE}/api/jobs/999999999", headers=hadmin, json={"title": "Missing"}, timeout=30)
    check(stale, 404, "missing job update")

    chat = check(requests.post(f"{BASE}/api/chat", headers=ha, json={"message": "What is the candidate's full name?", "resume_id": resume["id"], "job_id": job["id"]}, timeout=60), 200, "chat")
    assert chat["agent_used"] == "resume" and "Audit Candidate" in chat["reply"]
    cross_history = requests.get(f"{BASE}/api/chat/history", headers=hb, params={"resume_id": resume["id"], "job_id": job["id"]}, timeout=30)
    check(cross_history, 200, "cross-user history query")
    assert cross_history.json() == []

    logout_token = check(requests.post(f"{BASE}/api/auth/login", json={"email": user_a[0], "password": "Strong123"}, timeout=30), 200, "logout-test login")["access_token"]
    logout_headers = {"Authorization": f"Bearer {logout_token}"}
    check(requests.post(f"{BASE}/api/auth/logout", headers=logout_headers, timeout=30), 200, "logout")
    repeated_logout = requests.post(f"{BASE}/api/auth/logout", headers=logout_headers, timeout=30)
    check(repeated_logout, 401, "repeated logout safe rejection")

    deleted = requests.delete(f"{BASE}/api/jobs/{job['id']}", headers=hadmin, timeout=30)
    check(deleted, 200, "admin delete job")
    check(requests.get(f"{BASE}/api/jobs/{job['id']}", headers=ha, timeout=30), 404, "deleted job")
    remaining_history = check(requests.get(f"{BASE}/api/chat/history", headers=ha, params={"resume_id": resume["id"], "job_id": job["id"]}, timeout=30), 200, "deleted job history")
    assert remaining_history == []
    print("LIVE_PROJECT_AUDIT_PASS", {"resume_id": resume["id"], "job_id": job["id"], "checks": 18})

if __name__ == "__main__":
    main()
