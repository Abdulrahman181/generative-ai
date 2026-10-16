"""FastAPI application factory."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import middleware
from app.database import Base, SessionLocal, engine
from app.database.migrations import ensure_sqlite_schema
from app.exceptions import AppException
from app.exceptions.handlers import (
    app_exception_handler,
    http_exception_handler_wrapper,
    validation_exception_handler,
)
from app.routers import auth, chat, job, matching, resume, knowledge
from app.services.auth import ensure_default_admin
from app.services.job_seed import seed_default_jobs

import app.models                                     

               
ensure_sqlite_schema()
Base.metadata.create_all(bind=engine)
with SessionLocal() as _db:
    ensure_default_admin(_db)
    seed_default_jobs(_db)

     
app = FastAPI(
    title="CareerPilot API",
    version="4.0.0",
    description="AI-powered career guidance, resume analysis, job matching, and advisor support.",
)

            
middleware.register(app)

                    
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler_wrapper)

         
app.include_router(auth.router)
app.include_router(resume.router)
app.include_router(job.router)
app.include_router(matching.router)
app.include_router(chat.router)
app.include_router(knowledge.router)

@app.get("/api/health", tags=["Health"])
def health():
    return {"status": "ok"}


_frontend = Path(__file__).resolve().parent.parent / "frontend"
if _frontend.is_dir():
    app.mount("/", StaticFiles(directory=str(_frontend), html=True), name="frontend")
