"""FastAPI dependencies for authentication and database sessions."""

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database import get_db
from app.exceptions import ForbiddenError, UnauthorizedError
from app.models.user import User
from app.repositories import token_blacklist as blacklist_repo, user as user_repo

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated user from the Bearer token."""
    if token is None:
        raise UnauthorizedError("Could not validate credentials. Please log in again.")

    if blacklist_repo.is_blacklisted(db, token):
        raise UnauthorizedError("Could not validate credentials. Please log in again.")

    try:
        payload = decode_access_token(token)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise UnauthorizedError()
    except JWTError:
        raise UnauthorizedError("Could not validate credentials. Please log in again.")

    try:
        user = user_repo.find_by_id(db, int(user_id))
    except (TypeError, ValueError):
        raise UnauthorizedError("Could not validate credentials. Please log in again.")
    if user is None or not user.is_active:
        raise UnauthorizedError("Could not validate credentials. Please log in again.")
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise ForbiddenError("This action requires administrator privileges.")
    return current_user
