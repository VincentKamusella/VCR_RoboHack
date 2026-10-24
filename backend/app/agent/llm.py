"""Minimal client for a local Ollama server (standard library only)."""
from __future__ import annotations

import json
import logging
import threading
import urllib.error
import urllib.request
from typing import Protocol

log = logging.getLogger("pizzabot.llm")


class LLMError(RuntimeError):
    """The model could not be reached or returned something unusable."""


class LLMClient(Protocol):
    name: str

    def chat(self, messages: list[dict], *, schema: dict | None = None,
             temperature: float = 0.3, max_tokens: int = 300) -> str: ...


class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout: float = 60.0, keep_alive: str = "30m"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.name = model
        self.timeout = timeout
        self.keep_alive = keep_alive

    def _request(self, path: str, body: dict | None = None, timeout: float | None = None) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            f"{self.base_url}{path}", data=data,
            headers={"Content-Type": "application/json"} if data else {},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as res:
                return json.load(res)
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
            raise LLMError(f"Ollama request to {path} failed: {e}") from e

    def chat(self, messages: list[dict], *, schema: dict | None = None,
             temperature: float = 0.3, max_tokens: int = 300) -> str:
        body = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if schema is not None:
            body["format"] = schema
        out = self._request("/api/chat", body)
        content = (out.get("message") or {}).get("content", "")
        if not content.strip():
            raise LLMError("Ollama returned an empty message")
        return content

    def is_available(self) -> bool:
        """True when the server answers and the model is installed."""
        try:
            tags = self._request("/api/tags", timeout=3)
        except LLMError as e:
            log.warning("%s", e)
            return False
        names = {m.get("name") for m in tags.get("models", [])}
        wanted = {self.model, f"{self.model}:latest"}
        if names & wanted:
            return True
        log.warning("Model %s is not installed in Ollama (found: %s)", self.model, ", ".join(sorted(names)))
        return False

    def warm_up(self) -> None:
        """Load the model in the background so the first chat message is not slow."""
        def run():
            try:
                self.chat([{"role": "user", "content": "Hi"}], max_tokens=1)
                log.info("Model %s is loaded", self.model)
            except LLMError as e:
                log.warning("Warm-up failed: %s", e)
        threading.Thread(target=run, daemon=True).start()
