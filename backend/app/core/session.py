"""In-memory conversation state per chat session."""
from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass, field
from enum import Enum

from .text import Token


class DialogState(str, Enum):
    AWAITING_CHOICE = "awaiting_choice"   # waiting for the user to name a pizza
    CLARIFYING = "clarifying"             # asked "did you mean X or Y?"


@dataclass
class Session:
    id: str
    language: str = "en"
    # True once the user picked a language in the UI; replies then stay in that language.
    language_locked: bool = False
    state: DialogState = DialogState.AWAITING_CHOICE
    candidates: list[str] = field(default_factory=list)
    pending_exclusions: list[list[Token]] = field(default_factory=list)
    pending_message: str = ""
    # Set when the user's wording did not match any pizza; logged as a wish if they decline.
    pending_wish: tuple[str, str] | None = None
    last_active: float = field(default_factory=time.monotonic)

    def reset_pending(self) -> None:
        self.state = DialogState.AWAITING_CHOICE
        self.candidates = []
        self.pending_exclusions = []
        self.pending_message = ""
        self.pending_wish = None


class SessionStore:
    def __init__(self, ttl_seconds: int = 3600):
        self.ttl = ttl_seconds
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def create(self) -> Session:
        with self._lock:
            self._purge()
            session = Session(id=secrets.token_urlsafe(16))
            self._sessions[session.id] = session
            return session

    def get(self, session_id: str | None) -> Session | None:
        if not session_id:
            return None
        with self._lock:
            session = self._sessions.get(session_id)
            if session and time.monotonic() - session.last_active > self.ttl:
                del self._sessions[session_id]
                return None
            if session:
                session.last_active = time.monotonic()
            return session

    def _purge(self) -> None:
        now = time.monotonic()
        for sid in [s for s, v in self._sessions.items() if now - v.last_active > self.ttl]:
            del self._sessions[sid]
