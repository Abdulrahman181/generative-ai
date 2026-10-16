"""Recommendation data-access layer."""

from sqlalchemy.orm import Session

from app.models.recommendation import Recommendation


def delete_by_user_and_resume(db: Session, user_id: int, resume_id: int) -> None:
    db.query(Recommendation).filter(
        Recommendation.user_id == user_id,
        Recommendation.resume_id == resume_id,
    ).delete()


def find_existing(
    db: Session, user_id: int, resume_id: int, job_id: int
) -> Recommendation | None:
    return db.query(Recommendation).filter(
        Recommendation.user_id == user_id,
        Recommendation.resume_id == resume_id,
        Recommendation.job_id == job_id,
    ).first()


def create(db: Session, **kwargs) -> Recommendation:
    rec = Recommendation(**kwargs)
    db.add(rec)
    return rec                           


def find_by_user(
    db: Session, user_id: int, resume_id: int | None = None
) -> list[Recommendation]:
    q = db.query(Recommendation).filter(Recommendation.user_id == user_id)
    if resume_id:
        q = q.filter(Recommendation.resume_id == resume_id)
    return q.order_by(Recommendation.match_score.desc()).all()


def bulk_save(db: Session) -> None:
    db.commit()
