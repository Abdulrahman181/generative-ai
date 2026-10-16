"""Regression tests for the Career Advisor multi-claim / comparison fixes.

Run with:
    PYTHONPATH=<stubs>:. python3 tests/regression_career_advisor.py
"""
import asyncio

from app.agents.supervisor import run_supervisor
from app.schemas.job import JobOut


RESUME_TEXT = """ALEX MORGAN
Email: alex.morgan@example.com

SUMMARY
AI engineer with a track record shipping production ML systems.

SKILLS
Python, PyTorch, TensorFlow, Docker, FastAPI, Git, Linux, NumPy, Pandas,
PostgreSQL, Redis, SQL, Machine Learning
Soft skills: Collaboration, Communication, Leadership, Mentoring, Problem Solving

EXPERIENCE
Senior AI Engineer, Atlas Labs
January 2025 - Present
Led development of retrieval-augmented generation systems.

AI Engineer, Vertex Systems
August 2022 - December 2024
Built computer vision pipelines for fraud detection.

Machine Learning Engineer, Nimbus Data
July 2021 - July 2022
Built recommendation models.

EDUCATION
Bachelor of Science in Computer Science, State University, 2021

PROJECTS
AtlasRAG - retrieval augmented generation platform
FraudShield - real time fraud detection service
VisionTrack - computer vision tracking system
QuerySense - natural language query understanding tool
"""

RESUME_ITEM = {
    "id": 1,
    "filename": "alex_morgan.pdf",
    "full_name": "ALEX MORGAN",
    "contact": {"email": "alex.morgan@example.com"},
    "summary": "AI engineer with a track record shipping production ML systems.",
    "skills": {
        "technical": [
            "python", "pytorch", "tensorflow", "docker", "fastapi", "git", "linux",
            "numpy", "pandas", "postgresql", "redis", "sql", "machine learning",
        ],
        "soft": ["collaboration", "communication", "leadership", "mentoring", "problem solving"],
    },
    "education": [{"degree": "Bachelor of Science in Computer Science", "institution": "State University", "year": "2021"}],
    "experience": [
        {"title": "Senior AI Engineer", "company": "Atlas Labs", "duration": "January 2025 - Present"},
        {"title": "AI Engineer", "company": "Vertex Systems", "duration": "August 2022 - December 2024"},
        {"title": "Machine Learning Engineer", "company": "Nimbus Data", "duration": "July 2021 - July 2022"},
    ],
    "projects": [
        {"name": "AtlasRAG", "description": "retrieval augmented generation platform"},
        {"name": "FraudShield", "description": "real time fraud detection service"},
        {"name": "VisionTrack", "description": "computer vision tracking system"},
        {"name": "QuerySense", "description": "natural language query understanding tool"},
    ],
    "certifications": [],
    "training": [],
    "languages": [],
    "achievements": [],
}

RESUME_SKILLS = RESUME_ITEM["skills"]["technical"] + RESUME_ITEM["skills"]["soft"]

JOB = JobOut.model_construct(
    id=1,
    title="AI Engineer",
    company="Live Jobs",
    location="Remote",
    description="Build and ship production AI systems.",
    skills_required=["Python", "Machine Learning", "Kubernetes"],
    skills_preferred=["AWS"],
    experience_years="3+ years",
    education_required="Master's degree preferred",
    application_deadline=None,
    max_applications=None,
    application_count=0,
    applications_remaining=None,
    is_open=True,
    created_at=None,
    updated_at=None,
)


def run(question: str) -> dict:
    return asyncio.run(
        run_supervisor(
            question=question,
            resume_summary=RESUME_ITEM["summary"],
            resume_skills=RESUME_SKILLS,
            resume_text=RESUME_TEXT,
            history=[],
            available_jobs=[JOB],
            user_profile={"full_name": "Alex Morgan", "username": "alexm", "email": "alex.morgan@example.com"},
            resume_context=[RESUME_ITEM],
            selected_job=JOB,
        )
    )


failures = []


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}" + (f" — {detail}" if detail and status == "FAIL" else ""))
    if not condition:
        failures.append(label)


print("=" * 70)
print("TEST 1: full name + exact resume evidence")
r1 = run("What is the candidate's full name, and what exact resume evidence supports your answer?")
print(r1["reply"])
check("T1 route is resume", r1["agent_used"] == "resume")
check("T1 contains name", "ALEX MORGAN" in r1["reply"])
check("T1 contains actual evidence line (not just restated field)", "ALEX MORGAN" in r1["reply"] and ("source: raw resume text" in r1["reply"] or '"ALEX MORGAN' in r1["reply"]))

print("=" * 70)
print("TEST 2: explicit projects")
r2 = run("What projects are explicitly listed in the selected resume? Return only projects supported by the resume evidence.")
print(r2["reply"])
for proj in ("AtlasRAG", "FraudShield", "VisionTrack", "QuerySense"):
    check(f"T2 contains {proj}", proj in r2["reply"])

print("=" * 70)
print("TEST 3: selected job requirements")
r3 = run("What are the required skills and preferred skills of the currently selected AI Engineer job?")
print(r3["reply"])
check("T3 route is job", r3["agent_used"] == "job")
for term in ("Python", "Machine Learning", "Kubernetes", "AWS"):
    check(f"T3 contains {term}", term in r3["reply"])

print("=" * 70)
print("TEST 4: comparison — job requirements vs resume evidence")
r4 = run(
    "Which AI Engineer requirements are explicitly supported by the selected resume, and which are not "
    "supported? Do not infer missing skills from related technologies."
)
print(r4["reply"])
check("T4 route is comparison (not a plain resume skill dump)", r4["agent_used"] == "comparison")
check("T4: Python marked SUPPORTED", "Python | " in r4["reply"] and "SUPPORTED" in r4["reply"])
check("T4: Kubernetes marked NOT_SUPPORTED (no Docker-as-Kubernetes inference)", "Kubernetes | No explicit evidence. | NOT_SUPPORTED" in r4["reply"])
check("T4: AWS (preferred) marked NOT_SUPPORTED", "Preferred: AWS | No explicit evidence. | NOT_SUPPORTED" in r4["reply"])

print("=" * 70)
print("TEST 5: multi-claim yes/no with evidence")
r5 = run(
    "Does the selected resume explicitly mention AWS, Kubernetes, and 3+ years of experience? "
    "For each one, answer Yes or No and provide the supporting resume evidence. "
    "If there is no evidence, say 'No explicit evidence.'"
)
print(r5["reply"])
check("T5 route is resume", r5["agent_used"] == "resume")
check("T5: aws answered with No explicit evidence", "aws: No explicit evidence." in r5["reply"])
check("T5: kubernetes answered with No explicit evidence", "kubernetes: No explicit evidence." in r5["reply"])
check("T5: 3+ years experience answered Yes with dates", "3+ years of experience: Yes" in r5["reply"])
check("T5: no duplicated/corrupted text", r5["reply"].count("No explicit evidence.") <= 2)

print("=" * 70)
print("ADVERSARIAL A: many unrelated tech terms, none present")
rA = run("Does the resume mention AWS, Azure, Kubernetes, Docker, and Terraform?")
print(rA["reply"])
check("A: docker answered Yes (actually present)", "docker: Yes" in rA["reply"])
check("A: aws No", "aws: No explicit evidence." in rA["reply"])
check("A: azure No", "azure: No explicit evidence." in rA["reply"])
check("A: kubernetes No", "kubernetes: No explicit evidence." in rA["reply"])
check("A: terraform No (generic term, not hardcoded)", "terraform: No explicit evidence." in rA["reply"])

print("=" * 70)
print("ADVERSARIAL B: which-of phrasing")
rB = run("Which of Python, Java, Go, Kubernetes, and AWS are explicitly supported?")
print(rB["reply"])
check("B: python Yes", "python: Yes" in rB["reply"])
check("B: java No", "java: No explicit evidence." in rB["reply"])
check("B: go No", "go: No explicit evidence." in rB["reply"])

print("=" * 70)
print("ADVERSARIAL C: multi-field personal question")
rC = run("What are the candidate's name, degree, experience duration, and projects?")
print(rC["reply"])
check("C: name present", "ALEX MORGAN" in rC["reply"])
check("C: degree present", "Bachelor of Science" in rC["reply"])
check("C: experience present", "Atlas Labs" in rC["reply"] or "Vertex Systems" in rC["reply"])
check("C: projects present", "AtlasRAG" in rC["reply"])

print("=" * 70)
print("ADVERSARIAL D: negative-case personal topics never answered from resume")
rD = run("Does the resume mention the candidate's salary or political opinion?")
print(rD["reply"])
check("D: answers No explicit evidence rather than fabricating a value", "no explicit evidence" in rD["reply"].lower())
check("D: does not fabricate unrelated resume content as evidence (e.g. the QuerySense project line)", "QuerySense" not in rD["reply"])

print("=" * 70)
print("CONTEXT ISOLATION: resume-only question never uses job data as evidence")
rE = run("Does the resume explicitly mention Kubernetes?")
print(rE["reply"])
check("E: Kubernetes not fabricated as present just because the selected job requires it", "kubernetes: No explicit evidence." in rE["reply"])

print("=" * 70)
if failures:
    print(f"{len(failures)} CHECK(S) FAILED:")
    for f in failures:
        print(" -", f)
    raise SystemExit(1)
print("ALL CHECKS PASSED")
