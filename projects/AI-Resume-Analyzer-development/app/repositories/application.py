from sqlalchemy.orm import Session

from app.models.application import JobApplication


def find_by_job_and_user(db: Session, job_id: int, user_id: int) -> JobApplication | None:
    return db.query(JobApplication).filter(
        JobApplication.job_id == job_id,
        JobApplication.user_id == user_id,
    ).first()


def count_by_job(db: Session, job_id: int) -> int:
    return db.query(JobApplication).filter(JobApplication.job_id == job_id).count()


def create(db: Session, *, job_id: int, user_id: int, resume_id: int) -> JobApplication:
    application = JobApplication(job_id=job_id, user_id=user_id, resume_id=resume_id)
    db.add(application)
    db.flush()
    return application
