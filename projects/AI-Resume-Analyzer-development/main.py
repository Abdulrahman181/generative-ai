"""Entry point — re-exports the app instance from the ``app`` package.

Usage:
    uvicorn main:app --reload
    uvicorn app.main:app --reload   (also works)
"""

from app.main import app

__all__ = ["app"]
