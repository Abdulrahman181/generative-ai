from sqlalchemy.orm import Session

from app.agents import match_resume_to_jobs, match_resume_to_single_job
from app.exceptions import NotFoundError, ValidationError
from app.models.user import User
from app.repositories import job as job_repo, recommendation as rec_repo, resume as resume_repo
from app.schemas.matching import MatchResult, RecommendationOut
from app.services import job as job_svc
from app.utils import parse_json_dict


TOP_RECOMMENDATION_LIMIT = 3
TOP_APPLY_LIMIT = 5


def _extract_skills(resume) -> list[str]:
    data = parse_json_dict(resume.skills)
    if not data:
        return []
    return data.get("technical", []) + data.get("soft", [])


def _compute_matches(resume, jobs: list) -> list[MatchResult]:
    return match_resume_to_jobs(
        resume_skills=_extract_skills(resume),
        resume_text=resume.raw_text,
        resume_summary=resume.summary or "",
        jobs=jobs,
    )


async def get_recommendations(
    db: Session,
    user: User,
    resume_id: int,
    limit: int = TOP_RECOMMENDATION_LIMIT,
) -> list[MatchResult]:
    resume = resume_repo.find_by_id_and_user(db, resume_id, user.id)
    if not resume:
        raise NotFoundError("Resume not found or does not belong to you.")
    if not resume.raw_text:
        raise ValidationError("Resume has not been analyzed yet. Please re-upload.")

    jobs = job_svc.get_all_full(db)
    if not jobs:
        return []

    results = _compute_matches(resume, jobs)[:limit]
    for result in results:
        result.resume_id = resume.id
    _persist_batch(db, user.id, resume.id, results)
    return results


def get_top_match_job_ids(db: Session, user: User, resume_id: int) -> set[int]:
    """Return the current top-five open-job IDs for one owned, analyzed resume."""
    resume = resume_repo.find_by_id_and_user(db, resume_id, user.id)
    if not resume or not resume.raw_text:
        return set()
    jobs = job_svc.get_all_full(db)
    return {result.job.id for result in _compute_matches(resume, jobs)[:TOP_APPLY_LIMIT]}


async def match_single(db: Session, user: User, resume_id: int, job_id: int) -> MatchResult:
    resume = resume_repo.find_by_id_and_user(db, resume_id, user.id)
    if not resume:
        raise NotFoundError("Resume not found or does not belong to you.")
    if not resume.raw_text:
        raise ValidationError("Resume has not been analyzed yet. Please re-upload.")

    job = job_repo.find_by_id(db, job_id)
    if not job:
        raise NotFoundError("Job posting not found.")
    if not job_svc.is_open(job):
        raise ValidationError("This job is no longer open for matching.")

    job_out = job_svc.get(db, job_id)
    result = match_resume_to_single_job(
        resume_skills=_extract_skills(resume),
        resume_text=resume.raw_text,
        resume_summary=resume.summary or "",
        job=job_out,
    )
    result.resume_id = resume.id
    _persist_single(db, user.id, resume.id, result)
    return result


def get_saved(db: Session, user: User, resume_id: int | None = None) -> list[RecommendationOut]:
    recs = rec_repo.find_by_user(db, user.id, resume_id)
    results = []
    for recommendation in recs:
        job = job_repo.find_by_id(db, recommendation.job_id)
        results.append(RecommendationOut(
            id=recommendation.id,
            user_id=recommendation.user_id,
            resume_id=recommendation.resume_id,
            job_id=recommendation.job_id,
            match_score=recommendation.match_score,
            explanation=recommendation.explanation,
            job_title=job.title if job else None,
            job_company=job.company if job else None,
            created_at=recommendation.created_at,
        ))
    return results


def _persist_batch(db: Session, user_id: int, resume_id: int, results: list[MatchResult]) -> None:
    rec_repo.delete_by_user_and_resume(db, user_id, resume_id)
    for result in results:
        rec_repo.create(
            db,
            user_id=user_id,
            resume_id=resume_id,
            job_id=result.job.id,
            match_score=result.match_score,
            explanation=result.explanation,
        )
    rec_repo.bulk_save(db)


def _persist_single(db: Session, user_id: int, resume_id: int, result: MatchResult) -> None:
    existing = rec_repo.find_existing(db, user_id, resume_id, result.job.id)
    if existing:
        existing.match_score = result.match_score
        existing.explanation = result.explanation
    else:
        rec_repo.create(
            db,
            user_id=user_id,
            resume_id=resume_id,
            job_id=result.job.id,
            match_score=result.match_score,
            explanation=result.explanation,
        )
    rec_repo.bulk_save(db)
