"""Internal endpoints for other systems (robot, agent, admin), not for the chat frontend.

They are only mounted when PIZZABOT_INTERNAL_TOKEN is set, and every request must send
that token in the X-Internal-Token header.
"""
from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from ..container import Services


def _services(request: Request) -> Services:
    return request.app.state.services


def require_token(request: Request, x_internal_token: str = Header(default="")) -> None:
    expected = _services(request).settings.internal_api_token
    if not expected or not secrets.compare_digest(x_internal_token, expected):
        raise HTTPException(status_code=401, detail="invalid internal token")


router = APIRouter(prefix="/internal", tags=["internal"], dependencies=[Depends(require_token)])


@router.get("/orders")
def orders(request: Request, limit: int = 50) -> list[dict]:
    return _services(request).store.orders(limit=min(max(limit, 1), 500))


@router.get("/wishlist")
def wishlist(request: Request, status: str = "open") -> list[dict]:
    return _services(request).store.missing_pizzas(status or None)
