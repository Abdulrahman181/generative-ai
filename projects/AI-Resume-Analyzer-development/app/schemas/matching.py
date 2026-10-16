"""Matching and recommendation schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.job import JobOut


class MatchResult(BaseModel):
    status: Literal["ready"] = "ready"
    resume_id: int | None = None
    job: JobOut
    match_score: float
    explanation: str
    matched_skills: list[str] = Field(default_factory=list)
    matched_requirements: list[str] = Field(default_factory=list)
    partially_matched: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    improvement_suggestions: list[str] = Field(default_factory=list)


class RecommendationOut(BaseModel):
    status: Literal["ready"] = "ready"
    id: int
    user_id: int
    resume_id: int
    job_id: int
    match_score: float
    explanation: str | None
    job_title: str | None = None
    job_company: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True
