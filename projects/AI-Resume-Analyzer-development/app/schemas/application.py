from datetime import datetime

from pydantic import BaseModel


class JobApplicationOut(BaseModel):
    id: int
    job_id: int
    user_id: int
    resume_id: int
    job_title: str
    application_count: int
    applications_remaining: int | None
    created_at: datetime
