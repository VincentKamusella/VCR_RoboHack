"""Builds and wires the backend services in one place."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from .agent.agent import PizzaAgent
from .agent.llm import LLMClient, OllamaClient
from .config import Settings
from .core.dialog import DialogEngine
from .core.session import SessionStore
from .data.recipes import RecipeRepository
from .data.state_store import StateStore
from .services.order_sink import OrderSink, StoreOrderSink
from .services.wishlist import Wishlist

log = logging.getLogger("pizzabot")


@dataclass
class Services:
    settings: Settings
    recipes: RecipeRepository
    store: StateStore
    wishlist: Wishlist
    order_sink: OrderSink
    sessions: SessionStore
    engine: DialogEngine
    assistant: DialogEngine | PizzaAgent   # what the chat API talks to
    assistant_name: str                   # "rules" or the LLM model name


def build_assistant(settings: Settings, engine: DialogEngine,
                    llm: LLMClient | None = None) -> tuple[DialogEngine | PizzaAgent, str]:
    """The LLM agent when enabled and reachable, otherwise the rule engine on its own."""
    if llm is not None:
        return PizzaAgent(engine, llm), llm.name
    if settings.llm_mode == "off":
        return engine, "rules"
    client = OllamaClient(settings.ollama_url, settings.ollama_model, settings.llm_timeout_seconds)
    if client.is_available():
        client.warm_up()
        log.info("Chat agent: %s via Ollama at %s", client.model, settings.ollama_url)
        return PizzaAgent(engine, client), client.model
    if settings.llm_mode == "ollama":
        raise RuntimeError(
            f"PIZZABOT_LLM=ollama but {settings.ollama_model} is not available at {settings.ollama_url}. "
            "Start Ollama (`ollama serve`) and pull the model, or use PIZZABOT_LLM=auto."
        )
    log.warning("Ollama model %s not available, falling back to the rule-based chat", settings.ollama_model)
    return engine, "rules"


def build_services(settings: Settings, order_sink: OrderSink | None = None,
                   llm: LLMClient | None = None) -> Services:
    recipes = RecipeRepository(settings.recipe_db_path)
    store = StateStore(settings.state_db_path)
    wishlist = Wishlist(store)
    sink = order_sink or StoreOrderSink(store)
    engine = DialogEngine(recipes, sink, wishlist)
    assistant, name = build_assistant(settings, engine, llm)
    return Services(
        settings=settings,
        recipes=recipes,
        store=store,
        wishlist=wishlist,
        order_sink=sink,
        sessions=SessionStore(settings.session_ttl_seconds),
        engine=engine,
        assistant=assistant,
        assistant_name=name,
    )
