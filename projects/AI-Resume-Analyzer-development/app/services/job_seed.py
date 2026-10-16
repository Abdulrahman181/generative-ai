import json

from sqlalchemy.orm import Session

from app.rag.knowledge_base import DEFAULT_JSON
from app.repositories import job as job_repo


_EXTRA_JOBS = [
    {
        "title": "Data Engineer",
        "company": "Northstar Analytics",
        "location": "Remote",
        "description": "Build reliable data pipelines, transform large datasets, and maintain analytics infrastructure for product teams.",
        "skills_required": ["Python", "SQL", "ETL", "Airflow", "Cloud"],
        "experience_years": None,
        "education_required": None,
    },
    {
        "title": "Security Engineer",
        "company": "Shield Systems",
        "location": "Remote",
        "description": "Protect applications and infrastructure through security reviews, monitoring, incident response, and secure development practices.",
        "skills_required": ["Linux", "Python", "Networking", "Security", "Incident Response"],
        "experience_years": None,
        "education_required": None,
    },
    {
        "title": "Technical Support Engineer",
        "company": "CloudDesk",
        "location": "Hybrid",
        "description": "Resolve customer technical issues, investigate API integrations, document solutions, and collaborate with engineering teams.",
        "skills_required": ["APIs", "SQL", "Linux", "Troubleshooting", "Communication"],
        "experience_years": None,
        "education_required": None,
    },
]


def _structured_source_jobs(payload: dict) -> tuple[list[dict], dict[str, dict]]:
    jobs: list[dict] = []
    source_by_title: dict[str, dict] = {}
    seen_titles: set[str] = set()
    for entry in payload.get("knowledge_entries", []):
        title = str(entry.get("title", "")).strip()
        content = entry.get("content", "")
        if not title or title.endswith(" - Responsibility") or title in seen_titles or not isinstance(content, str) or not content.startswith("{"):
            continue
        try:
            job_data = json.loads(content)
        except json.JSONDecodeError:
            continue
        actual_title = job_data.get("title") or title
        source_by_title[actual_title] = job_data
        jobs.append({
            "title": actual_title,
            "company": "AI Resume Analyzer Jobs",
            "location": "Remote",
            "description": job_data.get("description") or entry.get("content", ""),
            "skills_required": job_data.get("required_skills") or [],
            "skills_preferred": job_data.get("preferred_skills") or [],
            "experience_years": job_data.get("experience_years"),
            "education_required": job_data.get("education"),
        })
        seen_titles.add(title)
        if len(jobs) == 22:
            break
    return jobs, source_by_title


def seed_default_jobs(db: Session) -> int:
    existing = job_repo.find_all(db)
    payload = json.loads(DEFAULT_JSON.read_text(encoding="utf-8"))
    source_jobs, source_by_title = _structured_source_jobs(payload)
    if existing:
        for job in existing:
            job_data = source_by_title.get(job.title)
            if not job_data:
                continue
            fields = {}
            if not job.experience_years and job_data.get("experience_years"):
                fields["experience_years"] = job_data["experience_years"]
            if not job.education_required and job_data.get("education"):
                fields["education_required"] = job_data["education"]
            if fields:
                job_repo.update(db, job, **fields)
        return 0

    jobs = source_jobs + _EXTRA_JOBS
    for job_data in jobs[:25]:
        job_repo.create(
            db,
            title=job_data["title"],
            company=job_data["company"],
            location=job_data["location"],
            description=job_data["description"],
            skills_required=json.dumps(job_data["skills_required"]),
            skills_preferred=json.dumps(job_data.get("skills_preferred", [])),
            experience_years=job_data.get("experience_years"),
            education_required=job_data.get("education_required"),
            application_count=0,
        )
    return min(len(jobs), 25)
