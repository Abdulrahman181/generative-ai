"""Authentication endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, oauth2_scheme
from app.models.user import User
from app.schemas import ErrorResponse
from app.schemas.auth import Token, UserCreate, UserLogin, UserOut
from app.services import auth as auth_svc

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorResponse}},
)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    return auth_svc.register(db, payload)


@router.post("/login", response_model=Token, responses={401: {"model": ErrorResponse}})
def login(payload: UserLogin, db: Session = Depends(get_db)):
    token, user = auth_svc.authenticate(db, payload)
    return Token(access_token=token, user=UserOut.model_validate(user))


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    token: str | None = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    auth_svc.logout(db, token)
    return {"detail": "Logged out successfully."}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
