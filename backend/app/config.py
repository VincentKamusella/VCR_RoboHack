"""Settings, read from environment variables with sensible defaults."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent
DEFAULT_RECIPE_DB = Path.home() / "pizza-db" / "build" / "pizza.db"


@dataclass(frozen=True)
class Settings:
    recipe_db_path: Path = DEFAULT_RECIPE_DB
    state_db_path: Path = BACKEND_DIR / "var" / "pizzabot.db"
    frontend_dir: Path | None = REPO_DIR / "frontend"
    session_ttl_seconds: int = 3600
    internal_api_token: str | None = None
    cors_origins: list[str] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.environ
        return cls(
            recipe_db_path=Path(env.get("PIZZA_DB_PATH", DEFAULT_RECIPE_DB)).expanduser(),
            state_db_path=Path(env.get("PIZZABOT_STATE_DB", BACKEND_DIR / "var" / "pizzabot.db")).expanduser(),
            frontend_dir=REPO_DIR / "frontend",
            session_ttl_seconds=int(env.get("PIZZABOT_SESSION_TTL", "3600")),
            internal_api_token=env.get("PIZZABOT_INTERNAL_TOKEN") or None,
            cors_origins=[o.strip() for o in env.get("PIZZABOT_CORS_ORIGINS", "").split(",") if o.strip()],
        )
