"""Career Advisor chat endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas import MessageResponse
from app.schemas.chat import ChatHistoryItem, ChatRequest, ChatResponse
from app.services import chat as chat_svc

router = APIRouter(prefix="/api/chat", tags=["Career Advisor"])


@router.post("", response_model=ChatResponse, summary="Send a career advice message")
async def send_message(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await chat_svc.chat(db, current_user, payload.message, payload.resume_id, payload.job_id)


@router.get("/history", response_model=list[ChatHistoryItem], summary="Get chat history")
def history(
    resume_id: int | None = Query(default=None),
    job_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return chat_svc.get_history(db, current_user, resume_id=resume_id, job_id=job_id)


@router.delete("/history", response_model=MessageResponse, summary="Clear chat history")
def clear(
    resume_id: int | None = Query(default=None),
    job_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    count = chat_svc.clear_history(db, current_user, resume_id=resume_id, job_id=job_id)
    return MessageResponse(detail=f"Cleared {count} messages.")
