"""FastAPI application.

Run from the backend folder with:  uvicorn app.main:create_app --factory --reload
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api import chat, internal
from .config import Settings
from .container import build_services
from .services.order_sink import OrderSink


def create_app(settings: Settings | None = None, order_sink: OrderSink | None = None) -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    settings = settings or Settings.from_env()
    app = FastAPI(title="Pizza Chatbot", version="1.0.0")
    app.state.services = build_services(settings, order_sink)

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type"],
        )

    app.include_router(chat.router)
    if settings.internal_api_token:
        app.include_router(internal.router)

    # Serve the frontend from the same origin. Mounted last so /api routes win.
    if settings.frontend_dir and settings.frontend_dir.is_dir():
        app.mount("/", StaticFiles(directory=settings.frontend_dir, html=True), name="frontend")
    return app

