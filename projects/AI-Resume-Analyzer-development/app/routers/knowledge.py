"""Knowledge base API — search and stats over app/rag/data."""

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_user
from app.models.user import User
from app.rag.knowledge_base import CATEGORIES, get_knowledge_base
from app.rag.retriever import Retriever

router = APIRouter(prefix="/api/knowledge", tags=["Knowledge Base"])


@router.get("/search")
def search_knowledge(
    q: str = Query(..., min_length=2, description="Search query"),
    category: str | None = Query(
        None,
        description="job_description | skill | career_roadmap | learning_resource | resume_guideline",
    ),
    top_k: int = Query(5, ge=1, le=20),
    mode: str = Query("hybrid", pattern="^(keyword|semantic|hybrid)$"),
    current_user: User = Depends(get_current_user),
):
    """Search the RAG knowledge base."""
    if category and category not in CATEGORIES:
        return {
            "query": q,
            "error": f"Invalid category. Use one of: {', '.join(CATEGORIES)}",
            "results": [],
        }

    retriever = Retriever(get_knowledge_base())
    chunks = retriever.retrieve(q, top_k=top_k, category=category, mode=mode)
    return {
        "query": q,
        "mode": mode,
        "category": category,
        "results": [
            {
                "id": c.entry_id,
                "category": c.category,
                "title": c.title,
                "content": c.content,
                "score": round(c.score, 4),
                "source": c.source,
            }
            for c in chunks
        ],
    }


@router.get("/stats")
def knowledge_stats(current_user: User = Depends(get_current_user)):
    """Return knowledge base size by category."""
    kb = get_knowledge_base()
    return kb.stats()


@router.get("/categories")
def knowledge_categories(current_user: User = Depends(get_current_user)):
    return {"categories": list(CATEGORIES)}
