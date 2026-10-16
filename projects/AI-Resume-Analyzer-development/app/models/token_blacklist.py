from sqlalchemy import Column, DateTime, Integer, String

from app.database import Base
from app.models.base import utcnow


class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(500), unique=True, index=True, nullable=False)
    blacklisted_at = Column(DateTime, default=utcnow, nullable=False)
