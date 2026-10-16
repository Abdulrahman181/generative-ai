from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import utcnow


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    company = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True, index=True)
    description = Column(Text, nullable=False)
    skills_required = Column(Text, nullable=True)
    skills_preferred = Column(Text, nullable=True)
    experience_years = Column(String(64), nullable=True)
    education_required = Column(Text, nullable=True)
    application_deadline = Column(DateTime, nullable=True)
    max_applications = Column(Integer, nullable=True)
    application_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=utcnow, nullable=False)

    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    recommendations = relationship("Recommendation", back_populates="job", cascade="all, delete-orphan")
    applications = relationship("JobApplication", backref="job", cascade="all, delete-orphan")
