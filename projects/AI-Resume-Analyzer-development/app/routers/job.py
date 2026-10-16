from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_admin
from app.models.user import User
from app.schemas import MessageResponse
from app.schemas.application import JobApplicationOut
from app.schemas.job import JobCreate, JobListItem, JobOut, JobUpdate
from app.services import application as application_svc
from app.services import job as job_svc

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


@router.post("", response_model=JobOut, status_code=status.HTTP_201_CREATED, summary="Add a job posting")
def add(payload: JobCreate, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return job_svc.create(db, payload)


@router.get("/search", response_model=list[JobListItem], summary="Search jobs")
def search(
    q: str | None = Query(None), location: str | None = Query(None),
    skill: str | None = Query(None),
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    return job_svc.search(db, query=q, location=location, skill=skill)


@router.get("", response_model=list[JobListItem], summary="List all jobs")
def list_all(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return job_svc.list_all(db)


@router.get("/{job_id}", response_model=JobOut, summary="View a job")
def get(job_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return job_svc.get(db, job_id)


@router.post("/{job_id}/apply", response_model=JobApplicationOut, status_code=status.HTTP_201_CREATED, summary="Apply to an open job")
async def apply(
    job_id: int,
    resume_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await application_svc.apply(db, current_user, job_id, resume_id)


@router.put("/{job_id}", response_model=JobOut, summary="Edit a job")
def edit(job_id: int, payload: JobUpdate, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    return job_svc.update(db, job_id, payload)


@router.delete("/{job_id}", response_model=MessageResponse, summary="Delete a job")
def remove(job_id: int, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    job_svc.delete(db, job_id)
    return MessageResponse(detail="Job posting deleted successfully.")
