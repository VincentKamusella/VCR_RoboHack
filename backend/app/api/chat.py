"""Public endpoints used by the frontend."""
from __future__ import annotations

from fastapi import APIRouter, Request

from ..container import Services
from ..models import ChatRequest, ChatResponse, Language, LanguageRequest, MenuResponse, SessionRequest
from ..services.menu import build_menu

router = APIRouter(prefix="/api", tags=["chat"])


def _services(request: Request) -> Services:
    return request.app.state.services


@router.get("/health")
def health(request: Request) -> dict:
    return {"status": "ok", "pizzas": len(_services(request).recipes.all())}


@router.post("/session", response_model=ChatResponse)
def start_session(request: Request, body: SessionRequest | None = None) -> ChatResponse:
    """Start a conversation in the language chosen in the UI (English by default)."""
    services = _services(request)
    session = services.sessions.create()
    reply = services.engine.set_language(session, (body or SessionRequest()).language)
    return ChatResponse(session_id=session.id, reply=reply.text,
                        language=session.language, suggestions=reply.suggestions)


@router.post("/session/language", response_model=ChatResponse)
def change_language(body: LanguageRequest, request: Request) -> ChatResponse:
    """Switch the conversation language. The reply is a fresh intro in that language."""
    services = _services(request)
    session = services.sessions.get(body.session_id) or services.sessions.create()
    reply = services.engine.set_language(session, body.language)
    return ChatResponse(session_id=session.id, reply=reply.text,
                        language=session.language, suggestions=reply.suggestions)


@router.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest, request: Request) -> ChatResponse:
    services = _services(request)
    session = services.sessions.get(body.session_id) or services.sessions.create()
    reply = services.engine.handle(session, body.message)
    # Only the text goes back. reply.order / reply.missing were already handled internally.
    return ChatResponse(session_id=session.id, reply=reply.text,
                        language=session.language, suggestions=reply.suggestions)


@router.get("/menu", response_model=MenuResponse)
def menu(request: Request, language: Language = "en") -> MenuResponse:
    """Every pizza with its ingredients, sorted alphabetically, for the menu book."""
    return MenuResponse(language=language, pizzas=build_menu(_services(request).recipes, language))
