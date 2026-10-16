"""Career Advisor chat schemas."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10_000)
    resume_id: int | None = None
    job_id: int | None = None

    @field_validator("message")
    @classmethod
    def clean_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be empty.")
        return value


class ChatResponse(BaseModel):
    reply: str
    sources: list[str] = Field(default_factory=list)
    resume_used: bool = False
    agent_used: str | None = None                                               


class ChatHistoryItem(BaseModel):
    id: int
    user_id: int
    role: str                        
    content: str
    resume_id: int | None = None
    job_id: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True
