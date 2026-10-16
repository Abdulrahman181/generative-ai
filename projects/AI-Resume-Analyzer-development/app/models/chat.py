"""Chat history model for career advisor conversations."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base
from app.models.base import utcnow


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)                        
    content = Column(Text, nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
