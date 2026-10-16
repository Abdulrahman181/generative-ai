import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.exceptions import NotFoundError
from app.models.job import Job
from app.repositories import chat as chat_repo, job as job_repo
from app.schemas.job import JobCreate, JobListItem, JobOut, JobUpdate
from app.utils import parse_json_list


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def is_open(job: Job, now: datetime | None = None) -> bool:
    current = now or datetime.now(timezone.utc)
    if job.max_applications is not None and job.application_count >= job.max_applications:
        return False
    if job.application_deadline is not None and _as_utc(job.application_deadline) <= current:
        return False
    return True


def applications_remaining(job: Job) -> int | None:
    if job.max_applications is None:
        return None
    return max(job.max_applications - job.application_count, 0)


def _to_out(job: Job) -> JobOut:
    return JobOut(
        id=job.id,
        title=job.title,
        company=job.company,
        location=job.location,
        description=job.description,
        skills_required=parse_json_list(job.skills_required),
        skills_preferred=parse_json_list(job.skills_preferred),
        experience_years=job.experience_years,
        education_required=job.education_required,
        application_deadline=job.application_deadline,
        max_applications=job.max_applications,
        application_count=job.application_count,
        applications_remaining=applications_remaining(job),
        is_open=is_open(job),
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def _to_list_item(job: Job) -> JobListItem:
    return JobListItem(
        id=job.id,
        title=job.title,
        company=job.company,
        location=job.location,
        skills_required=parse_json_list(job.skills_required),
        skills_preferred=parse_json_list(job.skills_preferred),
        experience_years=job.experience_years,
        education_required=job.education_required,
        application_deadline=job.application_deadline,
        max_applications=job.max_applications,
        application_count=job.application_count,
        applications_remaining=applications_remaining(job),
        is_open=is_open(job),
        created_at=job.created_at,
    )


def create(db: Session, payload: JobCreate) -> JobOut:
    job = job_repo.create(
        db,
        title=payload.title,
        company=payload.company,
        location=payload.location,
        description=payload.description,
        skills_required=json.dumps(payload.skills_required),
        skills_preferred=json.dumps(payload.skills_preferred),
        experience_years=payload.experience_years,
        education_required=payload.education_required,
        application_deadline=payload.application_deadline,
        max_applications=payload.max_applications,
        application_count=0,
    )
    return _to_out(job)


def update(db: Session, job_id: int, payload: JobUpdate) -> JobOut:
    job = job_repo.find_by_id(db, job_id)
    if not job:
        raise NotFoundError("Job posting not found.")

    sent = payload.model_fields_set
    fields: dict = {}
    for field in ("title", "company", "location", "description", "experience_years", "education_required", "application_deadline", "max_applications"):
        if field in sent:
            fields[field] = getattr(payload, field)
    if "skills_required" in sent:
        fields["skills_required"] = json.dumps(payload.skills_required or [])
    if "skills_preferred" in sent:
        fields["skills_preferred"] = json.dumps(payload.skills_preferred or [])

    job = job_repo.update(db, job, **fields)
    return _to_out(job)


def delete(db: Session, job_id: int) -> None:
    job = job_repo.find_by_id(db, job_id)
    if not job:
        raise NotFoundError("Job posting not found.")
    # Chat messages are not exposed through a Job relationship, so remove them
    # explicitly before the FK-backed job delete.
    chat_repo.delete_by_job(db, job.id)
    job_repo.delete(db, job)


def list_all(db: Session) -> list[JobListItem]:
    return [_to_list_item(job) for job in job_repo.find_all(db)]


def get(db: Session, job_id: int) -> JobOut:
    job = job_repo.find_by_id(db, job_id)
    if not job:
        raise NotFoundError("Job posting not found.")
    return _to_out(job)


def search(
    db: Session,
    query: str | None = None,
    location: str | None = None,
    skill: str | None = None,
) -> list[JobListItem]:
    return [_to_list_item(job) for job in job_repo.search(db, query=query, location=location, skill=skill)]


def get_all_full(db: Session) -> list[JobOut]:
    return [_to_out(job) for job in job_repo.find_all(db) if is_open(job)]
