"""Pins requested pizzas that are not in the recipe database, for adding them later."""
from __future__ import annotations

import logging

from ..data.state_store import StateStore

log = logging.getLogger("pizzabot.wishlist")


class Wishlist:
    def __init__(self, store: StateStore):
        self.store = store

    def add(self, requested: str, normalized: str, message: str, language: str | None) -> None:
        self.store.record_missing(requested, normalized, message, language)
        log.info("missing pizza requested: %r", requested)

    def open_items(self) -> list[dict]:
        return self.store.missing_pizzas("open")
