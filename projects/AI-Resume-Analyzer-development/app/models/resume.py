from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import utcnow


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    original_filename = Column(String(255), nullable=False)
    stored_filepath = Column(String(500), nullable=False)
    file_type = Column(String(10), nullable=False)

    raw_text = Column(Text, nullable=True)
    full_name = Column(String(255), nullable=True)
    contact_info = Column(Text, nullable=True)
    skills = Column(Text, nullable=True)
    education = Column(Text, nullable=True)
    experience = Column(Text, nullable=True)
    projects = Column(Text, nullable=True)
    training = Column(Text, nullable=True)
    languages = Column(Text, nullable=True)
    achievements = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    score = Column(Integer, nullable=True)
    strengths = Column(Text, nullable=True)
    weaknesses = Column(Text, nullable=True)
    improvement_recommendations = Column(Text, nullable=True)
    high_priority_fixes = Column(Text, nullable=True)
    impact_metrics = Column(Text, nullable=True)
    skills_ats_optimization = Column(Text, nullable=True)
    professional_summary_polish = Column(Text, nullable=True)
    improvement_job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    certifications = Column(Text, nullable=True)
    learning_resources = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utcnow, nullable=False)

    owner = relationship("User", back_populates="resumes")
    recommendations = relationship("Recommendation", back_populates="resume", cascade="all, delete-orphan")
    applications = relationship("JobApplication", back_populates="resume", cascade="all, delete-orphan")
    improvement_job = relationship("Job", foreign_keys=[improvement_job_id])
