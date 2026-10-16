from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.job import Job
from app.models.user import User
from app.repositories import application as application_repo
from app.repositories import job as job_repo
from app.repositories import resume as resume_repo
from app.schemas.application import JobApplicationOut
from app.services import matching as matching_svc
from app.services.job import applications_remaining, is_open


async def apply(db: Session, user: User, job_id: int, resume_id: int) -> JobApplicationOut:
    resume = resume_repo.find_by_id_and_user(db, resume_id, user.id)
    if not resume:
        raise NotFoundError("Resume not found or does not belong to you.")
    if not resume.raw_text:
        raise ValidationError("Resume has not been analyzed yet. Please re-upload.")

    job = job_repo.find_by_id(db, job_id)
    if not job:
        raise NotFoundError("Job posting not found.")
    if not is_open(job):
        raise ConflictError("This job is no longer accepting applications.")

    eligible_job_ids = matching_svc.get_top_match_job_ids(db, user, resume_id)
    if job_id not in eligible_job_ids:
        raise ValidationError("Applications are limited to the top five matching jobs for the selected resume.")

    if application_repo.find_by_job_and_user(db, job_id, user.id):
        raise ConflictError("You have already applied to this job.")

    job.application_count = application_repo.count_by_job(db, job_id)
    if not is_open(job):
        raise ConflictError("This job is no longer accepting applications.")

    # Reserve one application slot atomically. A count-then-increment sequence
    # can oversubscribe a capped job when two users apply concurrently.
    capacity_filter = [Job.id == job_id]
    if job.max_applications is not None:
        capacity_filter.append(Job.application_count < job.max_applications)
    updated = db.query(Job).filter(*capacity_filter).update(
        {Job.application_count: Job.application_count + 1},
        synchronize_session=False,
    )
    if updated != 1:
        db.rollback()
        raise ConflictError("This job is no longer accepting applications.")

    try:
        application = application_repo.create(
            db,
            job_id=job_id,
            user_id=user.id,
            resume_id=resume_id,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("You have already applied to this job.")
    db.refresh(application)
    db.refresh(job)
    return JobApplicationOut(
        id=application.id,
        job_id=job.id,
        user_id=user.id,
        resume_id=resume_id,
        job_title=job.title,
        application_count=job.application_count,
        applications_remaining=applications_remaining(job),
        created_at=application.created_at,
    )
