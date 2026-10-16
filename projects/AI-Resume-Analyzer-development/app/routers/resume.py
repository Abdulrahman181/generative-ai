"""Resume endpoints."""

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas import MessageResponse
from app.schemas.resume import ResumeImprovementOut, ResumeListItem, ResumeOut
from app.services import resume as resume_svc

router = APIRouter(prefix="/api/resumes", tags=["Resumes"])


@router.post("/upload", response_model=ResumeOut, status_code=status.HTTP_201_CREATED,
             summary="Upload and analyze a resume")
async def upload(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await resume_svc.upload_and_analyze(db, current_user, file)


@router.get("", response_model=list[ResumeListItem], summary="List user resumes")
def list_resumes(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return resume_svc.list_by_user(db, current_user)


@router.post("/{resume_id}/analyze", response_model=ResumeOut, summary="Analyze an uploaded resume")
async def analyze_existing(resume_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await resume_svc.reanalyze(db, current_user, resume_id)


@router.post("/{resume_id}/improvements", response_model=ResumeImprovementOut, summary="Generate job-specific resume improvement recommendations")
async def get_improvements(
    resume_id: int,
    job_id: int | None = Query(None, description="The exact matched job to use for these recommendations."),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await resume_svc.improvements(db, current_user, resume_id, job_id)


@router.get("/{resume_id}", response_model=ResumeOut, summary="Get resume details")
def get_resume(resume_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return resume_svc.get_by_id(db, current_user, resume_id)


@router.delete("/{resume_id}", response_model=MessageResponse, summary="Delete a resume")
def delete_resume(resume_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resume_svc.delete(db, current_user, resume_id)
    return MessageResponse(detail="Resume deleted successfully.")
