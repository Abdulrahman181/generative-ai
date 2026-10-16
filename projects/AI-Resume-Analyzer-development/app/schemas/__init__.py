"""Shared response models."""

from pydantic import BaseModel


class MessageResponse(BaseModel):
    detail: str


class ErrorResponse(BaseModel):
    detail: str
