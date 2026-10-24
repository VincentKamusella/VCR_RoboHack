"""Public API schemas. These are the only shapes the frontend ever sees.

Matched orders are deliberately absent: they stay inside the backend.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Language = Literal["en", "de"]


class SessionRequest(BaseModel):
    language: Language = "en"


class ChatRequest(BaseModel):
    session_id: str | None = Field(default=None, max_length=64)
    message: str = Field(min_length=1, max_length=500)


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    language: Language
    suggestions: list[str] = []


class MenuItem(BaseModel):
    name: str
    short_name: str
    ingredients: list[str]


class MenuIngredient(BaseModel):
    name: str        # name in the database (English)
    label: str       # name shown to the customer in the chosen language
    category: str


class MenuResponse(BaseModel):
    language: Language
    pizzas: list[MenuItem]
    ingredients: list[MenuIngredient]   # everything a custom pizza can be topped with
