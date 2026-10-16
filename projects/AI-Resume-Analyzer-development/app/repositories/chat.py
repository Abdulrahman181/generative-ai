from sqlalchemy.orm import Session

from app.models.chat import ChatMessage


def create(db: Session, **kwargs) -> ChatMessage:
    msg = ChatMessage(**kwargs)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def find_by_user(
    db: Session,
    user_id: int,
    limit: int = 50,
    resume_id: int | None = None,
    job_id: int | None = None,
) -> list[ChatMessage]:
    query = db.query(ChatMessage).filter(ChatMessage.user_id == user_id)
    if resume_id is None:
        query = query.filter(ChatMessage.resume_id.is_(None))
    else:
        query = query.filter(ChatMessage.resume_id == resume_id)
    if job_id is None:
        query = query.filter(ChatMessage.job_id.is_(None))
    else:
        query = query.filter(ChatMessage.job_id == job_id)
    return query.order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc()).limit(limit).all()[::-1]


def delete_by_job(db: Session, job_id: int) -> int:
    count = db.query(ChatMessage).filter(ChatMessage.job_id == job_id).delete(synchronize_session=False)
    db.commit()
    return count


def delete_by_user(
    db: Session,
    user_id: int,
    resume_id: int | None = None,
    job_id: int | None = None,
) -> int:
    query = db.query(ChatMessage).filter(ChatMessage.user_id == user_id)
    if resume_id is None:
        query = query.filter(ChatMessage.resume_id.is_(None))
    else:
        query = query.filter(ChatMessage.resume_id == resume_id)
    if job_id is None:
        query = query.filter(ChatMessage.job_id.is_(None))
    else:
        query = query.filter(ChatMessage.job_id == job_id)
    count = query.delete()
    db.commit()
    return count
