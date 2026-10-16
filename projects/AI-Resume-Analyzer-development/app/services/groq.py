"""Small async-compatible Groq client with strict response normalization."""

import asyncio
import json
import re

import requests

from app.core import GROQ_API_KEY, GROQ_API_URL, GROQ_MODEL


class GroqUnavailableError(RuntimeError):
    """Raised when the external provider cannot return a usable JSON object."""


async def complete_json(system_prompt: str, user_prompt: str) -> dict:
    if not GROQ_API_KEY:
        raise GroqUnavailableError("GROQ_API_KEY is not configured.")
    payload = {
        "model": GROQ_MODEL,
        "temperature": 0.2,
        "max_tokens": 1800,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    try:
        response = await asyncio.to_thread(
            requests.post,
            GROQ_API_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=45,
        )
    except requests.RequestException as exc:
        raise GroqUnavailableError("Groq request could not be completed.") from exc
    if response.status_code >= 400:
        raise GroqUnavailableError(f"Groq request failed with status {response.status_code}.")
    try:
        content = response.json()["choices"][0]["message"]["content"]
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        raw = str(content).strip()
        fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", raw, flags=re.IGNORECASE | re.DOTALL)
        if fenced:
            raw = fenced.group(1).strip()
        parsed = json.loads(raw)
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise GroqUnavailableError("Groq returned an invalid JSON response.") from exc
    if not isinstance(parsed, dict):
        raise GroqUnavailableError("Groq returned a JSON value instead of an object.")
    return parsed
