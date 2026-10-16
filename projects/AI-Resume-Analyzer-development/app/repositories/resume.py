"""Resume data-access layer."""

from sqlalchemy.orm import Session

from app.models.resume import Resume


def create(db: Session, **kwargs) -> Resume:
    resume = Resume(**kwargs)
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


def find_by_user(db: Session, user_id: int) -> list[Resume]:
    return (
        db.query(Resume)
        .filter(Resume.user_id == user_id)
        .order_by(Resume.created_at.desc())
        .all()
    )


def find_by_id_and_user(db: Session, resume_id: int, user_id: int) -> Resume | None:
    return db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == user_id,
    ).first()


def delete(db: Session, resume: Resume) -> None:
    db.delete(resume)
    db.commit()
