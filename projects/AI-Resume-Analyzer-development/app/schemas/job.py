from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class JobCreate(BaseModel):
    title: str
    company: str | None = None
    location: str | None = None
    description: str
    skills_required: list[str] = Field(default_factory=list)
    skills_preferred: list[str] = Field(default_factory=list)
    experience_years: str | None = None
    education_required: str | None = None
    application_deadline: datetime | None = None
    max_applications: int | None = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Job title cannot be empty.")
        return value

    @field_validator("description")
    @classmethod
    def description_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Job description cannot be empty.")
        return value

    @field_validator("skills_required", "skills_preferred")
    @classmethod
    def clean_skills(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(skill.strip() for skill in value if skill.strip()))

    @field_validator("max_applications")
    @classmethod
    def valid_max_applications(cls, value: int | None) -> int | None:
        if value is not None and value < 1:
            raise ValueError("Maximum applications must be at least 1.")
        return value


class JobUpdate(BaseModel):
    title: str | None = None
    company: str | None = None
    location: str | None = None
    description: str | None = None
    skills_required: list[str] | None = None
    skills_preferred: list[str] | None = None
    experience_years: str | None = None
    education_required: str | None = None
    application_deadline: datetime | None = None
    max_applications: int | None = None

    @field_validator("title", "description")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be empty.")
        return value

    @field_validator("skills_required", "skills_preferred")
    @classmethod
    def clean_optional_skills(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        return list(dict.fromkeys(skill.strip() for skill in value if skill.strip()))

    @field_validator("max_applications")
    @classmethod
    def valid_optional_max_applications(cls, value: int | None) -> int | None:
        if value is not None and value < 1:
            raise ValueError("Maximum applications must be at least 1.")
        return value


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    company: str | None
    location: str | None
    description: str
    skills_required: list[str]
    skills_preferred: list[str]
    experience_years: str | None
    education_required: str | None
    application_deadline: datetime | None
    max_applications: int | None
    application_count: int
    applications_remaining: int | None
    is_open: bool
    created_at: datetime
    updated_at: datetime


class JobListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    company: str | None
    location: str | None
    skills_required: list[str]
    skills_preferred: list[str]
    experience_years: str | None
    education_required: str | None
    application_deadline: datetime | None
    max_applications: int | None
    application_count: int
    applications_remaining: int | None
    is_open: bool
    created_at: datetime
