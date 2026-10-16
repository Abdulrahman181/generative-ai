from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SkillSet(BaseModel):
    technical: list[str] = Field(default_factory=list)
    soft: list[str] = Field(default_factory=list)
    programming_languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    libraries: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    cloud: list[str] = Field(default_factory=list)
    machine_learning: list[str] = Field(default_factory=list)
    data_science: list[str] = Field(default_factory=list)
    ai: list[str] = Field(default_factory=list)
    computer_vision: list[str] = Field(default_factory=list)
    nlp: list[str] = Field(default_factory=list)


class ContactInfo(BaseModel):
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    linkedin: str | None = None
    github: str | None = None


class EducationEntry(BaseModel):
    degree: str | None = None
    institution: str | None = None
    year: str | None = None
    details: str | None = None


class ExperienceEntry(BaseModel):
    title: str | None = None
    company: str | None = None
    duration: str | None = None
    description: str | None = None


class ProjectEntry(BaseModel):
    name: str | None = None
    technologies: list[str] = Field(default_factory=list)
    description: str | None = None


class ResumeAnalysis(BaseModel):
    full_name: str | None = None
    contact: ContactInfo = Field(default_factory=ContactInfo)
    skills: SkillSet = Field(default_factory=SkillSet)
    education: list[EducationEntry] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    training: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    summary: str = ""
    score: float = 0.0
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    learning_resources: list[str] = Field(default_factory=list)


class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    original_filename: str
    file_type: str
    raw_text: str | None = None
    full_name: str | None = None
    contact: ContactInfo = Field(default_factory=ContactInfo)
    skills: SkillSet | None = None
    education: list[EducationEntry] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    training: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    summary: str | None = None
    score: float | None = None
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    improvement_recommendations: list[str] = Field(default_factory=list)
    high_priority_fixes: list[str] = Field(default_factory=list)
    impact_metrics: list[str] = Field(default_factory=list)
    skills_ats_optimization: list[str] = Field(default_factory=list)
    professional_summary_polish: list[str] = Field(default_factory=list)
    learning_resources: list[str] = Field(default_factory=list)
    improvement_job_id: int | None = None
    state: Literal["ready"] = "ready"
    created_at: datetime


class ResumeListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    file_type: str
    summary: str | None = None
    score: float | None = None
    created_at: datetime


class ResumeImprovementOut(BaseModel):
    state: Literal["ready"] = "ready"
    scope: Literal["general", "job_specific"]
    resume_id: int
    job_id: int | None = None
    job_title: str | None = None
    job_company: str | None = None
    score: float
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    high_priority_fixes: list[str] = Field(default_factory=list)
    impact_metrics: list[str] = Field(default_factory=list)
    skills_ats_optimization: list[str] = Field(default_factory=list)
    professional_summary_polish: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    learning_resources: list[str] = Field(default_factory=list)
