"""ORM model registry — import every model so ``Base.metadata.create_all``
discovers all tables."""

from app.models.user import User              
from app.models.resume import Resume              
from app.models.job import Job              
from app.models.recommendation import Recommendation              
from app.models.token_blacklist import TokenBlacklist              
from app.models.chat import ChatMessage
from app.models.application import JobApplication

__all__ = [
    "User",
    "Resume",
    "Job",
    "Recommendation",
    "TokenBlacklist",
    "ChatMessage",
    "JobApplication",
]
