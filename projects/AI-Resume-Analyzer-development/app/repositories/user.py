from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.user import User


def find_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def find_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def find_by_identifier(db: Session, identifier: str) -> User | None:
    return db.query(User).filter(or_(User.email == identifier, User.username == identifier)).first()


def find_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def create(
    db: Session, *, email: str, username: str | None, full_name: str | None,
    hashed_password: str, is_admin: bool = False,
) -> User:
    user = User(
        email=email, username=username, full_name=full_name,
        hashed_password=hashed_password, is_admin=is_admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def count(db: Session) -> int:
    return db.query(User).count()
