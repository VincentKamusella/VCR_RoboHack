"""The chatbot's own SQLite file: matched orders and requested pizzas that are missing from the menu.

This is deliberately separate from the recipe database, which is a read-only build artifact.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS missing_pizzas (
    normalized         TEXT PRIMARY KEY,
    requested          TEXT NOT NULL,
    request_count      INTEGER NOT NULL DEFAULT 1,
    first_requested_at TEXT NOT NULL,
    last_requested_at  TEXT NOT NULL,
    last_message       TEXT NOT NULL,
    language           TEXT,
    status             TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'added', 'rejected'))
);

CREATE TABLE IF NOT EXISTS orders (
    id          INTEGER PRIMARY KEY,
    order_id    TEXT NOT NULL UNIQUE,
    created_at  TEXT NOT NULL,
    session_id  TEXT NOT NULL,
    pizza_name  TEXT NOT NULL,
    payload     TEXT NOT NULL
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class StateStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    # --- missing pizzas -------------------------------------------------------------

    def record_missing(self, requested: str, normalized: str, message: str, language: str | None) -> None:
        ts = now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO missing_pizzas
                    (normalized, requested, first_requested_at, last_requested_at, last_message, language)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(normalized) DO UPDATE SET
                    request_count     = request_count + 1,
                    last_requested_at = excluded.last_requested_at,
                    last_message      = excluded.last_message
                """,
                (normalized, requested, ts, ts, message, language),
            )

    def missing_pizzas(self, status: str | None = "open") -> list[dict]:
        sql = "SELECT * FROM missing_pizzas"
        args: tuple = ()
        if status:
            sql += " WHERE status = ?"
            args = (status,)
        sql += " ORDER BY request_count DESC, last_requested_at DESC"
        with self._connect() as conn:
            return [dict(r) for r in conn.execute(sql, args)]

    def set_missing_status(self, normalized: str, status: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE missing_pizzas SET status = ? WHERE normalized = ?", (status, normalized)
            )
            return cur.rowcount > 0

    # --- orders ---------------------------------------------------------------------

    def add_order(self, order: dict) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO orders (order_id, created_at, session_id, pizza_name, payload) VALUES (?, ?, ?, ?, ?)",
                (order["order_id"], order["created_at"], order["session_id"],
                 order["pizza"]["name"], json.dumps(order, ensure_ascii=False)),
            )

    def orders(self, limit: int = 50) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT payload FROM orders ORDER BY id DESC LIMIT ?", (limit,))
            return [json.loads(r["payload"]) for r in rows]
