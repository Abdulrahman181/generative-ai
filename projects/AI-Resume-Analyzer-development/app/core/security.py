from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from app.core import ALGORITHM, SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _bcrypt_safe_password(plain: str) -> str:
    encoded = plain.encode("utf-8")[:72]
    return encoded.decode("utf-8", errors="ignore")


def hash_password(plain: str) -> str:
    return _pwd_ctx.hash(_bcrypt_safe_password(plain))


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(_bcrypt_safe_password(plain), hashed)


def create_access_token(
    data: dict[str, str],
    expires_delta: timedelta | None = None,
) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload["exp"] = expire
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
