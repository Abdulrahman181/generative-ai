"""Token blacklist data-access layer."""

from sqlalchemy.orm import Session

from app.models.token_blacklist import TokenBlacklist


def is_blacklisted(db: Session, token: str) -> bool:
    return db.query(TokenBlacklist).filter(TokenBlacklist.token == token).first() is not None


def blacklist(db: Session, token: str) -> None:
    if is_blacklisted(db, token):
        return
    db.add(TokenBlacklist(token=token))
    db.commit()
