import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.core import MIN_PASSWORD_LENGTH


class UserCreate(BaseModel):
    email: EmailStr
    username: str | None = None
    full_name: str | None = None
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("username")
    @classmethod
    def valid_username(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9_]{3,64}", value):
            raise ValueError("Username must contain 3-64 letters, numbers, or underscores.")
        return value

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        if len(value) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
        if len(value) > 72:
            raise ValueError("Password must be 72 characters or fewer.")
        if not re.search(r"[A-Za-z]", value):
            raise ValueError("Password must contain at least one letter.")
        if not re.search(r"\d", value):
            raise ValueError("Password must contain at least one number.")
        return value

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            return None
        return value.strip() if value is not None else None


class UserLogin(BaseModel):
    email: EmailStr | None = None
    username: str | None = None
    password: str = Field(min_length=1)

    @field_validator("username")
    @classmethod
    def clean_username(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def require_identifier(self):
        if not self.email and not self.username:
            raise ValueError("Email or username is required.")
        return self


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str | None
    email: EmailStr
    full_name: str | None
    is_admin: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
