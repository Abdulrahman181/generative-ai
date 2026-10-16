"""Job data-access layer."""

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.job import Job


def create(db: Session, **kwargs) -> Job:
    job = Job(**kwargs)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def find_by_id(db: Session, job_id: int) -> Job | None:
    return db.query(Job).filter(Job.id == job_id).first()


def find_all(db: Session) -> list[Job]:
    return db.query(Job).order_by(Job.created_at.desc()).all()


def update(db: Session, job: Job, **fields) -> Job:
    for key, val in fields.items():
        setattr(job, key, val)
    db.commit()
    db.refresh(job)
    return job


def delete(db: Session, job: Job) -> None:
    db.delete(job)
    db.commit()


def search(
    db: Session,
    *,
    query: str | None = None,
    location: str | None = None,
    skill: str | None = None,
) -> list[Job]:
    q = db.query(Job)
    if query:
        pattern = f"%{query}%"
        q = q.filter(or_(
            Job.title.ilike(pattern),
            Job.description.ilike(pattern),
            Job.company.ilike(pattern),
        ))
    if location:
        q = q.filter(Job.location.ilike(f"%{location}%"))
    if skill:
        skill_pattern = f"%{skill}%"
        q = q.filter(or_(
            Job.skills_required.ilike(skill_pattern),
            Job.skills_preferred.ilike(skill_pattern),
        ))
    return q.order_by(Job.created_at.desc()).all()
