"""Public API schemas. These are the only shapes the frontend ever sees.

Matched recipes are deliberately absent: they stay inside the backend.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class SessionResponse(BaseModel):
    session_id: str
    reply: str
    suggestions: list[str] = []


class ChatRequest(BaseModel):
    session_id: str | None = Field(default=None, max_length=64)
    message: str = Field(min_length=1, max_length=500)


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    suggestions: list[str] = []
