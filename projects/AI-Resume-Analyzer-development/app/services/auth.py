from sqlalchemy.orm import Session

from app.core import ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_USERNAME
from app.core.security import create_access_token, hash_password, verify_password
from app.exceptions import ConflictError, ForbiddenError, UnauthorizedError
from app.models.user import User
from app.repositories import token_blacklist as blacklist_repo, user as user_repo
from app.schemas.auth import UserCreate, UserLogin


def register(db: Session, payload: UserCreate) -> User:
    if user_repo.find_by_email(db, payload.email):
        raise ConflictError("An account with this email already exists.")
    if payload.username and user_repo.find_by_username(db, payload.username):
        raise ConflictError("An account with this username already exists.")

    # Administrator access is provisioned only through the configured bootstrap
    # account; an empty database must not turn an arbitrary registrant into admin.
    return user_repo.create(
        db,
        email=payload.email,
        username=payload.username,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        is_admin=False,
    )


def ensure_default_admin(db: Session) -> User:
    user = user_repo.find_by_username(db, ADMIN_USERNAME) or user_repo.find_by_email(db, ADMIN_EMAIL)
    if user is None:
        return user_repo.create(
            db,
            email=ADMIN_EMAIL,
            username=ADMIN_USERNAME,
            full_name="Abdulrahman",
            hashed_password=hash_password(ADMIN_PASSWORD),
            is_admin=True,
        )

    changed = False
    if user.username != ADMIN_USERNAME:
        user.username = ADMIN_USERNAME
        changed = True
    if user.email != ADMIN_EMAIL:
        user.email = ADMIN_EMAIL
        changed = True
    if user.full_name != "Abdulrahman":
        user.full_name = "Abdulrahman"
        changed = True
    if not user.is_admin:
        user.is_admin = True
        changed = True
    if not user.is_active:
        user.is_active = True
        changed = True
    if changed:
        db.commit()
        db.refresh(user)
    return user


def authenticate(db: Session, payload: UserLogin) -> tuple[str, User]:
    identifier = payload.username or str(payload.email)
    user = user_repo.find_by_identifier(db, identifier)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise UnauthorizedError("Incorrect email or password.")
    if not user.is_active:
        raise ForbiddenError("This account has been deactivated.")

    token = create_access_token(data={"sub": str(user.id)})
    return token, user


def logout(db: Session, token: str) -> None:
    blacklist_repo.blacklist(db, token)
