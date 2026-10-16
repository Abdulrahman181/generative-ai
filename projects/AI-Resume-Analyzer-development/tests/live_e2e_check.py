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
    return response.json() if response.content else None


def make_docx() -> io.BytesIO:
    document = Document()
    for line in (
        "Live E2E Candidate",
        "Python FastAPI SQL Docker",
        "Bachelor of Science in Computer Science, Live University, 2024",
        "Software Engineer at Live Corp, 2022-2024",
        "Built APIs and improved deployment reliability by 30 percent.",
    ):
        document.add_paragraph(line)
    buffer = io.BytesIO()
    document.save(buffer)
    buffer.seek(0)
    return buffer


def main() -> None:
    health = requests.get(f"{BASE}/api/health", timeout=30)
    expect(health, 200, "health")
    assert requests.get(f"{BASE}/", timeout=30).status_code == 200

    email = f"live-{uuid.uuid4().hex[:10]}@example.com"
    password = "Strong123"
    expect(requests.post(f"{BASE}/api/auth/register", json={"email": email, "password": password, "full_name": "Live E2E User"}, timeout=30), 201, "register")
    token = expect(requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": password}, timeout=30), 200, "login")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    admin_token = expect(requests.post(f"{BASE}/api/auth/login", json={"email": os.environ["ADMIN_EMAIL"], "password": os.environ["ADMIN_PASSWORD"]}, timeout=30), 200, "admin login")["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    upload = requests.post(
        f"{BASE}/api/resumes/upload",
        headers=headers,
        files={"file": ("live.docx", make_docx(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        timeout=60,
    )
    resume = expect(upload, 201, "resume upload")
    assert resume["raw_text"]

    jobs = []
    for index in range(5):
        jobs.append(expect(requests.post(f"{BASE}/api/jobs", headers=admin_headers, json={"title": f"Live Python Role {index}", "company": "Live Corp", "description": "Build APIs and services.", "skills_required": ["Python"]}, timeout=30), 201, f"create top job {index}"))
    outside = expect(requests.post(f"{BASE}/api/jobs", headers=admin_headers, json={"title": "Live Zig Role", "company": "Other Corp", "description": "Build systems.", "skills_required": ["Zig"]}, timeout=30), 201, "create outside job")

    matches = expect(requests.post(f"{BASE}/api/match/{resume['id']}?limit=5", headers=headers, timeout=60), 200, "top-five match")
    ranked_ids = [item["job"]["id"] for item in matches]
    assert len(ranked_ids) == 5 and outside["id"] not in ranked_ids

    applied = expect(requests.post(f"{BASE}/api/jobs/{ranked_ids[0]}/apply", headers=headers, params={"resume_id": resume["id"]}, timeout=30), 201, "eligible apply")
    assert applied["job_id"] == ranked_ids[0]
    rejected = requests.post(f"{BASE}/api/jobs/{outside['id']}/apply", headers=headers, params={"resume_id": resume["id"]}, timeout=30)
    expect(rejected, 422, "ineligible apply")

    job_a, job_b = jobs[0], jobs[1]
    for job in (job_a, job_b):
        chat = expect(requests.post(f"{BASE}/api/chat", headers=headers, json={"message": "What are the requirements for this role?", "resume_id": resume["id"], "job_id": job["id"]}, timeout=60), 200, f"chat job {job['id']}")
        assert chat["reply"]
    history_a = expect(requests.get(f"{BASE}/api/chat/history", headers=headers, params={"resume_id": resume["id"], "job_id": job_a["id"]}, timeout=30), 200, "history A")
    history_b = expect(requests.get(f"{BASE}/api/chat/history", headers=headers, params={"resume_id": resume["id"], "job_id": job_b["id"]}, timeout=30), 200, "history B")
    assert {row["job_id"] for row in history_a} == {job_a["id"]}
    assert {row["job_id"] for row in history_b} == {job_b["id"]}

    cleared = expect(requests.delete(f"{BASE}/api/chat/history", headers=headers, params={"resume_id": resume["id"], "job_id": job_a["id"]}, timeout=30), 200, "clear job A history")
    assert cleared["detail"].startswith("Cleared ")
    assert expect(requests.get(f"{BASE}/api/chat/history", headers=headers, params={"resume_id": resume["id"], "job_id": job_a["id"]}, timeout=30), 200, "empty history A") == []
    assert expect(requests.get(f"{BASE}/api/chat/history", headers=headers, params={"resume_id": resume["id"], "job_id": job_b["id"]}, timeout=30), 200, "history B preserved")
    print("LIVE_E2E_PASS", {"resume_id": resume["id"], "top_five": ranked_ids, "applied_job_id": applied["job_id"], "rejected_status": rejected.status_code})


if __name__ == "__main__":
    main()
