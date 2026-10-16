"""Resume orchestration service — upload → extract → analyze → persist."""

import json
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.exceptions import NotFoundError, ValidationError
from app.models.user import User
from app.repositories import chat as chat_repo, job as job_repo, recommendation as recommendation_repo, resume as resume_repo
from app.schemas.resume import (
    ContactInfo,
    EducationEntry,
    ExperienceEntry,
    ProjectEntry,
    ResumeImprovementOut,
    ResumeListItem,
    ResumeOut,
    SkillSet,
)
from app.services import file as file_svc, job as job_svc
from app.agents import analyze_resume
from app.agents.job_matcher import match_resume_to_single_job
from app.agents.resume_analyzer import get_improvement_recommendations
from app.utils import parse_json_dict, parse_json_list


def _to_out(r) -> ResumeOut:
    skills_data = parse_json_dict(r.skills)
    return ResumeOut(
        id=r.id,
        user_id=r.user_id,
        original_filename=r.original_filename,
        file_type=r.file_type,
        raw_text=r.raw_text,
        full_name=r.full_name,
        contact=ContactInfo(**(parse_json_dict(r.contact_info) or {})),
        skills=SkillSet(**skills_data) if skills_data else None,
        education=parse_json_list(r.education, EducationEntry),
        experience=parse_json_list(r.experience, ExperienceEntry),
        projects=parse_json_list(r.projects, ProjectEntry),
        certifications=parse_json_list(r.certifications) or [],
        training=parse_json_list(r.training) or [],
        languages=parse_json_list(r.languages) or [],
        achievements=parse_json_list(r.achievements) or [],
        summary=r.summary,
        score=r.score,
        strengths=parse_json_list(r.strengths) or [],
        weaknesses=parse_json_list(r.weaknesses) or [],
        improvement_recommendations=parse_json_list(r.improvement_recommendations) or [],
        high_priority_fixes=parse_json_list(r.high_priority_fixes) or [],
        impact_metrics=parse_json_list(r.impact_metrics) or [],
        skills_ats_optimization=parse_json_list(r.skills_ats_optimization) or [],
        professional_summary_polish=parse_json_list(r.professional_summary_polish) or [],
        learning_resources=parse_json_list(r.learning_resources) or [],
        improvement_job_id=r.improvement_job_id,
        created_at=r.created_at,
    )


async def upload_and_analyze(db: Session, user: User, file: UploadFile) -> ResumeOut:
    ext = file_svc.validate_upload(file)
    stored_path: str | None = None
    try:
        stored_path = await file_svc.save_file(file, ext)
        raw_text = file_svc.extract_text(stored_path, ext)
        analysis = await analyze_resume(raw_text)

        resume = resume_repo.create(
            db,
            user_id=user.id,
            original_filename=file.filename,
            stored_filepath=stored_path,
            file_type=ext,
            raw_text=raw_text,
            full_name=analysis.full_name,
            contact_info=json.dumps(analysis.contact.model_dump()),
            skills=json.dumps(analysis.skills.model_dump()),
            education=json.dumps([e.model_dump() for e in analysis.education]),
            experience=json.dumps([e.model_dump() for e in analysis.experience]),
            projects=json.dumps([e.model_dump() for e in analysis.projects]),
            training=json.dumps(analysis.training),
            languages=json.dumps(analysis.languages),
            achievements=json.dumps(analysis.achievements),
            summary=analysis.summary,
            score=analysis.score,
            strengths=json.dumps(analysis.strengths),
            weaknesses=json.dumps(analysis.weaknesses),
            improvement_recommendations=json.dumps([]),
            high_priority_fixes=json.dumps([]),
            impact_metrics=json.dumps([]),
            skills_ats_optimization=json.dumps([]),
            professional_summary_polish=json.dumps([]),
            certifications=json.dumps(analysis.certifications),
            learning_resources=json.dumps(analysis.learning_resources),
        )
        return _to_out(resume)
    except Exception:
        if stored_path:
            Path(stored_path).unlink(missing_ok=True)
        raise


async def reanalyze(db: Session, user: User, resume_id: int) -> ResumeOut:
    resume = resume_repo.find_by_id_and_user(db, resume_id, user.id)
    if not resume:
        raise NotFoundError("Resume not found or does not belong to you.")
    if not resume.raw_text:
        raise NotFoundError("Resume text is not available for analysis.")
    analysis = await analyze_resume(resume.raw_text)
    resume.full_name = analysis.full_name
    resume.contact_info = json.dumps(analysis.contact.model_dump())
    resume.skills = json.dumps(analysis.skills.model_dump())
    resume.education = json.dumps([entry.model_dump() for entry in analysis.education])
    resume.experience = json.dumps([entry.model_dump() for entry in analysis.experience])
    resume.projects = json.dumps([entry.model_dump() for entry in analysis.projects])
    resume.training = json.dumps(analysis.training)
    resume.languages = json.dumps(analysis.languages)
    resume.achievements = json.dumps(analysis.achievements)
    resume.summary = analysis.summary
    resume.score = analysis.score
    resume.strengths = json.dumps(analysis.strengths)
    resume.weaknesses = json.dumps(analysis.weaknesses)
    resume.improvement_recommendations = json.dumps([])
    resume.high_priority_fixes = json.dumps([])
    resume.impact_metrics = json.dumps([])
    resume.skills_ats_optimization = json.dumps([])
    resume.professional_summary_polish = json.dumps([])
    resume.improvement_job_id = None
    recommendation_repo.delete_by_user_and_resume(db, user.id, resume.id)

    resume.certifications = json.dumps(analysis.certifications)
    resume.learning_resources = json.dumps(analysis.learning_resources)
    db.commit()
    db.refresh(resume)
    return _to_out(resume)


async def improvements(db: Session, user: User, resume_id: int, job_id: int | None = None) -> ResumeImprovementOut:
    resume = resume_repo.find_by_id_and_user(db, resume_id, user.id)
    if not resume:
        raise NotFoundError("Resume not found or does not belong to you.")
    if not resume.raw_text:
        raise NotFoundError("Resume text is not available for recommendations.")
    job = None
    job_out = None
    match_result = None
    if job_id is not None:
        saved_match = recommendation_repo.find_existing(db, user.id, resume.id, job_id)
        if saved_match is None:
            raise ValidationError("Run matching for this exact resume and job before requesting recommendations.")
        job = job_repo.find_by_id(db, job_id)
        if not job:
            raise NotFoundError("The selected matched job is no longer available.")
        job_out = job_svc.get(db, job.id)

    analysis = await analyze_resume(resume.raw_text)
    if job_out is not None:
        resume_skills = analysis.skills.technical + analysis.skills.soft
        match_result = match_resume_to_single_job(
            resume_skills=resume_skills,
            resume_text=resume.raw_text,
            resume_summary=analysis.summary,
            job=job_out,
        )
    recommendations = await get_improvement_recommendations(resume.raw_text, analysis, job_out, match_result)
    recommendations.resume_id = resume.id
    resume.score = recommendations.score
    resume.strengths = json.dumps(recommendations.strengths)
    resume.weaknesses = json.dumps(recommendations.weaknesses)
    resume.improvement_recommendations = json.dumps(recommendations.recommendations)
    resume.high_priority_fixes = json.dumps(recommendations.high_priority_fixes)
    resume.impact_metrics = json.dumps(recommendations.impact_metrics)
    resume.skills_ats_optimization = json.dumps(recommendations.skills_ats_optimization)
    resume.professional_summary_polish = json.dumps(recommendations.professional_summary_polish)
    resume.improvement_job_id = job.id if job is not None else None
    resume.certifications = json.dumps(recommendations.certifications)
    resume.learning_resources = json.dumps(recommendations.learning_resources)
    db.commit()
    return recommendations


def list_by_user(db: Session, user: User) -> list[ResumeListItem]:
    rows = resume_repo.find_by_user(db, user.id)
    return [
        ResumeListItem(
                        id=r.id, original_filename=r.original_filename,
            file_type=r.file_type,
            summary=r.summary,
            score=r.score,

            created_at=r.created_at,
        )
        for r in rows
    ]


def get_by_id(db: Session, user: User, resume_id: int) -> ResumeOut:
    resume = resume_repo.find_by_id_and_user(db, resume_id, user.id)
    if not resume:
        raise NotFoundError("Resume not found or does not belong to you.")
    return _to_out(resume)


def delete(db: Session, user: User, resume_id: int) -> None:
    resume = resume_repo.find_by_id_and_user(db, resume_id, user.id)
    if not resume:
        raise NotFoundError("Resume not found or does not belong to you.")
    stored_path = Path(resume.stored_filepath)
    chat_repo.delete_by_user(db, user.id, resume_id=resume.id)
    recommendation_repo.delete_by_user_and_resume(db, user.id, resume.id)
    resume_repo.delete(db, resume)
    stored_path.unlink(missing_ok=True)
