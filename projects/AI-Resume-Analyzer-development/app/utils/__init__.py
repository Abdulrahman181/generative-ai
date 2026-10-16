"""Reusable JSON helpers for JSON-encoded DB columns."""

import json
from typing import TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


def parse_json_list(raw: str | None, model: type[T] | None = None) -> list:
    """Parse a JSON-encoded list column, optionally hydrating each item."""
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            return []
        if model:
            parsed = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                try:
                    parsed.append(model(**item))
                except ValidationError:
                    continue
            return parsed
        return data
    except (json.JSONDecodeError, TypeError):
        return []


def parse_json_dict(raw: str | None) -> dict | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, TypeError):
        return None


def encode_json(obj) -> str:
    """Encode a value (list, dict, or Pydantic model) to a JSON string."""
    if isinstance(obj, BaseModel):
        return json.dumps(obj.model_dump())
    return json.dumps(obj)
