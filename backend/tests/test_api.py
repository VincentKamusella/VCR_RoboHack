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
    assert set(body) == {"session_id", "reply", "language", "suggestions"}   # no recipe data leaks out
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
    assert client.get("/api/health").json() == {"status": "ok", "pizzas": 16, "assistant": "rules"}


def test_session_defaults_to_english(client):
    body = client.post("/api/session").json()
    assert body["language"] == "en"
    assert body["reply"].startswith("Hi!")


def test_session_in_german(client):
    body = client.post("/api/session", json={"language": "de"}).json()
    assert body["language"] == "de"
    assert body["reply"].startswith("Hallo!")


def test_chosen_language_sticks(client):
    sid = client.post("/api/session", json={"language": "de"}).json()["session_id"]
    # The chosen language wins even when the user writes in English.
    reply = client.post("/api/chat", json={"session_id": sid, "message": "Salami please"}).json()
    assert reply["reply"].startswith("Gute Wahl")
    assert reply["language"] == "de"


def test_language_must_be_supported(client):
    assert client.post("/api/session", json={"language": "fr"}).status_code == 422
    assert client.get("/api/menu?language=fr").status_code == 422


def test_menu_is_alphabetical_with_ingredients(client):
    pizzas = client.get("/api/menu").json()["pizzas"]
    short = [p["short_name"] for p in pizzas]
    assert short[:3] == ["BBQ Chicken", "Calzone", "Capricciosa"]
    assert short == sorted(short, key=lambda n: n.lower().replace("ö", "o"))
    hawaii = next(p for p in pizzas if p["name"] == "Pizza Hawaii")
    assert hawaii["ingredients"] == ["Tomato Sauce", "Mozzarella", "Cooked Ham", "Pineapple"]


def test_menu_in_german(client):
    pizzas = client.get("/api/menu?language=de").json()["pizzas"]
    hawaii = next(p for p in pizzas if p["name"] == "Pizza Hawaii")
    assert hawaii["ingredients"] == ["Tomatensoße", "Mozzarella", "Kochschinken", "Ananas"]
