"""Builds and wires the backend services in one place."""
from __future__ import annotations

from dataclasses import dataclass

from .config import Settings
from .core.dialog import DialogEngine
from .core.session import SessionStore
from .data.recipes import RecipeRepository
from .data.state_store import StateStore
from .services.order_sink import OrderSink, StoreOrderSink
from .services.wishlist import Wishlist


@dataclass
class Services:
    settings: Settings
    recipes: RecipeRepository
    store: StateStore
    wishlist: Wishlist
    order_sink: OrderSink
    sessions: SessionStore
    engine: DialogEngine


def build_services(settings: Settings, order_sink: OrderSink | None = None) -> Services:
    recipes = RecipeRepository(settings.recipe_db_path)
    store = StateStore(settings.state_db_path)
    wishlist = Wishlist(store)
    sink = order_sink or StoreOrderSink(store)
    return Services(
        settings=settings,
        recipes=recipes,
        store=store,
        wishlist=wishlist,
        order_sink=sink,
        sessions=SessionStore(settings.session_ttl_seconds),
        engine=DialogEngine(recipes, sink, wishlist),
    )
