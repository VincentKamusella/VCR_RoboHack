"""Read-only access to the pizza-db SQLite database (built by the separate pizza-db project)."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


class RecipeDatabaseError(RuntimeError):
    pass


@dataclass(frozen=True)
class Ingredient:
    name: str
    category: str


@dataclass(frozen=True)
class Recipe:
    id: int
    slug: str
    name: str
    style: str
    origin: str
    ingredients: tuple[Ingredient, ...]


class RecipeRepository:
    """Loads every recipe once. The menu is small, so it is kept in memory."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self._recipes: list[Recipe] = []
        self._ingredients: dict[str, str] = {}
        self.reload()

    def reload(self) -> None:
        if not self.db_path.exists():
            raise RecipeDatabaseError(
                f"Recipe database not found at {self.db_path}. "
                "Build it with `make build` in the pizza-db project or set PIZZA_DB_PATH."
            )
        conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        try:
            self._ingredients = dict(conn.execute("SELECT name, category FROM ingredients"))
            rows = conn.execute(
                """
                SELECT p.id, p.slug, p.name, p.style, p.origin, i.name, i.category
                  FROM pizzas p
                  JOIN pizza_ingredients pi ON pi.pizza_id = p.id
                  JOIN ingredients i ON i.id = pi.ingredient_id
                 ORDER BY p.name, pi.position
                """
            ).fetchall()
        except sqlite3.Error as e:
            raise RecipeDatabaseError(f"Could not read {self.db_path}: {e}") from e
        finally:
            conn.close()

        grouped: dict[int, dict] = {}
        for pid, slug, name, style, origin, ing_name, ing_cat in rows:
            entry = grouped.setdefault(
                pid, {"id": pid, "slug": slug, "name": name, "style": style, "origin": origin, "ingredients": []}
            )
            entry["ingredients"].append(Ingredient(ing_name, ing_cat))
        self._recipes = [
            Recipe(**{**e, "ingredients": tuple(e["ingredients"])}) for e in grouped.values()
        ]

    def all(self) -> list[Recipe]:
        return list(self._recipes)

    def get(self, name: str) -> Recipe | None:
        return next((r for r in self._recipes if r.name == name), None)

    def ingredient_categories(self) -> dict[str, str]:
        """Every ingredient in the database, mapped to its category."""
        return dict(self._ingredients)
