from sqlalchemy.orm import Session

from app.agents.supervisor import run_supervisor
from app.exceptions import NotFoundError
from app.models.user import User
from app.repositories import chat as chat_repo, job as job_repo, resume as resume_repo
from app.schemas.chat import ChatHistoryItem, ChatResponse
from app.services import job as job_svc
from app.utils import parse_json_dict, parse_json_list


def _extract_skills(resume) -> list[str]:
    data = parse_json_dict(resume.skills)
    if not data:
        return []
    return data.get("technical", []) + data.get("soft", [])


def _resume_context(resumes) -> list[dict]:
    result = []
    for resume in resumes:
        skills = parse_json_dict(resume.skills) or {}
        result.append({
            "id": resume.id,
            "filename": resume.original_filename,
            "full_name": resume.full_name,
            "contact": parse_json_dict(resume.contact_info) or {},
            "summary": resume.summary,
            "skills": skills,
            "education": parse_json_list(resume.education),
            "experience": parse_json_list(resume.experience),
            "projects": parse_json_list(resume.projects),
            "certifications": parse_json_list(resume.certifications),
            "training": parse_json_list(resume.training),
            "languages": parse_json_list(resume.languages),
            "achievements": parse_json_list(resume.achievements),
        })
    return result


async def chat(
    db: Session, user: User, message: str, resume_id: int | None = None, job_id: int | None = None
) -> ChatResponse:
    selected_resume = None
    if resume_id is not None:
        selected_resume = resume_repo.find_by_id_and_user(db, resume_id, user.id)
        if not selected_resume:
            raise NotFoundError("Resume not found or does not belong to you.")
    selected_job = job_repo.find_by_id(db, job_id) if job_id else None
    if job_id and not selected_job:
        raise NotFoundError("Job posting not found.")
    selected_job_out = job_svc.get(db, job_id) if selected_job else None

    resume_summary = selected_resume.summary if selected_resume else None
    resume_skills = _extract_skills(selected_resume) if selected_resume else []
    resume_text = selected_resume.raw_text if selected_resume else None
    profile = {
        "full_name": user.full_name,
        "username": user.username,
        "email": user.email,
    }
    history_rows = chat_repo.find_by_user(db, user.id, limit=10, resume_id=resume_id, job_id=job_id)
    history = [{"role": row.role, "content": row.content} for row in history_rows]

    chat_repo.create(
        db,
        user_id=user.id,
        role="user",
        content=message,
        resume_id=resume_id,
        job_id=job_id,
    )

    result = await run_supervisor(
        question=message,
        resume_summary=resume_summary,
        resume_skills=resume_skills,
        resume_text=resume_text,
        history=history,
        available_jobs=job_svc.get_all_full(db),
        user_profile=profile,
        resume_context=_resume_context([selected_resume]) if selected_resume else [],
        selected_job=selected_job_out,
    )

    chat_repo.create(
        db,
        user_id=user.id,
        role="assistant",
        content=result["reply"],
        resume_id=resume_id,
        job_id=job_id,
    )

    return ChatResponse(
        reply=result["reply"],
        sources=result.get("sources", []),
        resume_used=result.get("resume_used", False),
        agent_used=result.get("agent_used"),
    )


def get_history(
    db: Session,
    user: User,
    resume_id: int | None = None,
    job_id: int | None = None,
) -> list[ChatHistoryItem]:
    rows = chat_repo.find_by_user(db, user.id, limit=50, resume_id=resume_id, job_id=job_id)
    return [
        ChatHistoryItem(
            id=row.id, user_id=row.user_id, role=row.role,
            content=row.content,
            resume_id=row.resume_id,
            job_id=row.job_id,
            created_at=row.created_at,
        )
        for row in rows
    ]


def clear_history(
    db: Session,
    user: User,
    resume_id: int | None = None,
    job_id: int | None = None,
) -> int:
    return chat_repo.delete_by_user(db, user.id, resume_id=resume_id, job_id=job_id)
