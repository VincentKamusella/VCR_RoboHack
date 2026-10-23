import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.order_sink import MemoryOrderSink


@pytest.fixture
def sink():
    return MemoryOrderSink()


@pytest.fixture
def client(settings, sink):
    return TestClient(create_app(settings, order_sink=sink))


def test_session_and_chat_flow(client, sink):
    start = client.post("/api/session").json()
    assert start["session_id"] and "pizza" in start["reply"].lower()

    res = client.post("/api/chat", json={"session_id": start["session_id"], "message": "Hawaii without pineapple"})
    assert res.status_code == 200
    body = res.json()
    assert set(body) == {"session_id", "reply", "suggestions"}   # no recipe data leaks out
    assert body["session_id"] == start["session_id"]
    assert sink.orders[0]["removed_ingredients"] == ["Pineapple"]


def test_unknown_session_gets_a_new_one(client):
    body = client.post("/api/chat", json={"session_id": "nope", "message": "Margherita"}).json()
    assert body["session_id"] != "nope"


def test_message_validation(client):
    assert client.post("/api/chat", json={"message": ""}).status_code == 422
    assert client.post("/api/chat", json={"message": "x" * 501}).status_code == 422


def test_internal_routes_hidden_without_token(client):
    assert client.get("/internal/orders").status_code == 404


def test_internal_routes_with_token(settings, sink):
    from dataclasses import replace
    client = TestClient(create_app(replace(settings, internal_api_token="secret"), order_sink=sink))
    assert client.get("/internal/wishlist").status_code == 401
    client.post("/api/chat", json={"message": "Pizza Lahmacun"})
    res = client.get("/internal/wishlist", headers={"X-Internal-Token": "secret"})
    assert res.status_code == 200
    assert res.json()[0]["requested"] == "Lahmacun"


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok", "pizzas": 16}
