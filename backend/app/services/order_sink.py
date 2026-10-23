"""Where matched pizzas go. This is the internal hand-off point; the user never sees it.

To connect a robot or an agent later, write a class with a `submit(order)` method and pass
it to `build_services` (see app/container.py). Nothing else needs to change.
"""
from __future__ import annotations

import logging
from typing import Protocol

from ..data.state_store import StateStore

log = logging.getLogger("pizzabot.orders")


class OrderSink(Protocol):
    def submit(self, order: dict) -> None: ...


class StoreOrderSink:
    """Default sink: persists every order in the bot's state database and logs it."""

    def __init__(self, store: StateStore):
        self.store = store

    def submit(self, order: dict) -> None:
        self.store.add_order(order)
        log.info("order %s: %s, removed=%s", order["order_id"], order["pizza"]["name"], order["removed_ingredients"])


class MemoryOrderSink:
    """Keeps orders in a list. Handy for tests and for in-process consumers."""

    def __init__(self):
        self.orders: list[dict] = []

    def submit(self, order: dict) -> None:
        self.orders.append(order)


class FanOutOrderSink:
    """Sends each order to several sinks."""

    def __init__(self, *sinks: OrderSink):
        self.sinks = sinks

    def submit(self, order: dict) -> None:
        for sink in self.sinks:
            sink.submit(order)
