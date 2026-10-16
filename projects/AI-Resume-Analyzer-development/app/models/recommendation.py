from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import utcnow


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)

    match_score = Column(Float, nullable=False)
    explanation = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utcnow, nullable=False)

    user = relationship("User", back_populates="recommendations")
    resume = relationship("Resume", back_populates="recommendations")
    job = relationship("Job", back_populates="recommendations")
