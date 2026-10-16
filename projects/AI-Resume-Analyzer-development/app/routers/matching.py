"""Matching & recommendation endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.matching import MatchResult, RecommendationOut
from app.services import matching as matching_svc

router = APIRouter(prefix="/api", tags=["Matching & Recommendations"])


@router.post("/match/{resume_id}", response_model=list[MatchResult], summary="Match resume against all jobs")
async def match_all(
    resume_id: int,
    limit: int = Query(default=matching_svc.TOP_RECOMMENDATION_LIMIT, ge=1, le=matching_svc.TOP_APPLY_LIMIT),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await matching_svc.get_recommendations(db, current_user, resume_id, limit=limit)


@router.post("/match/{resume_id}/{job_id}", response_model=MatchResult, summary="Match resume against one job")
async def match_one(resume_id: int, job_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await matching_svc.match_single(db, current_user, resume_id, job_id)


@router.get("/recommendations", response_model=list[RecommendationOut], summary="Saved recommendations")
def saved(resume_id: int | None = Query(None), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return matching_svc.get_saved(db, current_user, resume_id)
