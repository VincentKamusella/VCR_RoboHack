"""Shared fixtures: a small recipe database with the same schema as pizza-db."""
import sqlite3
from pathlib import Path

import pytest

from app.config import Settings
from app.core.dialog import DialogEngine
from app.core.session import Session
from app.data.recipes import RecipeRepository
from app.data.state_store import StateStore
from app.services.order_sink import MemoryOrderSink
from app.services.wishlist import Wishlist

INGREDIENTS = {
    "Tomato Sauce": "sauce", "Mozzarella": "cheese", "Gorgonzola": "cheese", "Parmesan": "cheese",
    "Fontina": "cheese", "Ricotta": "cheese", "Salami": "meat", "Spicy Salami": "meat",
    "Cooked Ham": "meat", "Chicken": "meat", "Döner Meat": "meat", "Tuna": "seafood",
    "Mushrooms": "vegetable", "Artichokes": "vegetable", "Black Olives": "vegetable",
    "Onion": "vegetable", "Red Onion": "vegetable", "Garlic": "vegetable", "Chili Peppers": "vegetable",
    "Tomato Slices": "vegetable", "Bell Peppers": "vegetable", "Corn": "vegetable",
    "Pineapple": "fruit", "Basil": "herb", "Oregano": "herb", "Olive Oil": "other",
    "Garlic Yogurt Sauce": "sauce", "BBQ Sauce": "sauce", "Cilantro": "herb",
}
PIZZAS = {
    "Pizza Margherita": ["Tomato Sauce", "Mozzarella", "Basil", "Olive Oil"],
    "Pizza Marinara": ["Tomato Sauce", "Garlic", "Oregano", "Olive Oil"],
    "Pizza Salami": ["Tomato Sauce", "Mozzarella", "Salami"],
    "Pizza Salami e Funghi": ["Tomato Sauce", "Mozzarella", "Salami", "Mushrooms"],
    "Pizza Funghi": ["Tomato Sauce", "Mozzarella", "Mushrooms"],
    "Pizza Prosciutto": ["Tomato Sauce", "Mozzarella", "Cooked Ham"],
    "Pizza Capricciosa": ["Tomato Sauce", "Mozzarella", "Cooked Ham", "Mushrooms", "Artichokes", "Black Olives"],
    "Pizza Quattro Stagioni": ["Tomato Sauce", "Mozzarella", "Cooked Ham", "Mushrooms", "Artichokes", "Black Olives"],
    "Pizza Quattro Formaggi": ["Mozzarella", "Gorgonzola", "Parmesan", "Fontina"],
    "Pizza Hawaii": ["Tomato Sauce", "Mozzarella", "Cooked Ham", "Pineapple"],
    "Pizza Tonno": ["Tomato Sauce", "Mozzarella", "Tuna", "Red Onion"],
    "Pizza Diavola": ["Tomato Sauce", "Mozzarella", "Spicy Salami", "Chili Peppers"],
    "Pizza Calzone": ["Tomato Sauce", "Mozzarella", "Ricotta", "Salami", "Cooked Ham"],
    "Pizza Döner": ["Tomato Sauce", "Mozzarella", "Döner Meat", "Onion", "Tomato Slices", "Garlic Yogurt Sauce"],
    "Pizza Chicken": ["Tomato Sauce", "Mozzarella", "Chicken", "Bell Peppers", "Corn"],
    "BBQ Chicken Pizza": ["BBQ Sauce", "Mozzarella", "Chicken", "Red Onion", "Cilantro"],
}


def build_recipe_db(path: Path) -> Path:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE ingredients (id INTEGER PRIMARY KEY, name TEXT UNIQUE, category TEXT, diet TEXT);
        CREATE TABLE pizzas (id INTEGER PRIMARY KEY, slug TEXT, name TEXT UNIQUE, style TEXT,
                             origin TEXT, description TEXT);
        CREATE TABLE pizza_ingredients (pizza_id INTEGER, ingredient_id INTEGER, position INTEGER);
        """
    )
    ids = {}
    for name, cat in INGREDIENTS.items():
        ids[name] = conn.execute(
            "INSERT INTO ingredients (name, category, diet) VALUES (?, ?, 'vegan')", (name, cat)
        ).lastrowid
    for name, ings in PIZZAS.items():
        pid = conn.execute(
            "INSERT INTO pizzas (slug, name, style, origin, description) VALUES (?, ?, 'Test', 'Test', '')",
            (name.lower().replace(" ", "-"), name),
        ).lastrowid
        conn.executemany(
            "INSERT INTO pizza_ingredients VALUES (?, ?, ?)",
            [(pid, ids[i], pos) for pos, i in enumerate(ings, 1)],
        )
    conn.commit()
    conn.close()
    return path


@pytest.fixture
def recipe_db(tmp_path):
    return build_recipe_db(tmp_path / "pizza.db")


@pytest.fixture
def settings(tmp_path, recipe_db):
    return Settings(recipe_db_path=recipe_db, state_db_path=tmp_path / "state.db", frontend_dir=None)


@pytest.fixture
def store(settings):
    return StateStore(settings.state_db_path)


@pytest.fixture
def sink():
    return MemoryOrderSink()


@pytest.fixture
def engine(recipe_db, store, sink):
    return DialogEngine(RecipeRepository(recipe_db), sink, Wishlist(store))


@pytest.fixture
def chat(engine):
    """Send messages in one session: chat("Margherita") -> Reply."""
    session = Session(id="test")

    def send(text):
        return engine.handle(session, text)

    send.session = session
    return send
