"""The public menu shown in the frontend's menu book: pizza names and their ingredients.

This is menu information, like a printed menu. Matched orders stay internal (see order_sink).
"""
from __future__ import annotations

from ..core.ingredients import ingredient_display_name
from ..core.text import fold
from ..data.recipes import RecipeRepository


def short_name(name: str) -> str:
    """'Pizza Margherita' -> 'Margherita', 'BBQ Chicken Pizza' -> 'BBQ Chicken'."""
    if name.startswith("Pizza "):
        return name[len("Pizza "):]
    if name.endswith(" Pizza"):
        return name[: -len(" Pizza")]
    return name


def build_menu(recipes: RecipeRepository, language: str) -> list[dict]:
    """All pizzas, sorted alphabetically by their distinctive name."""
    items = [
        {
            "name": recipe.name,
            "short_name": short_name(recipe.name),
            "ingredients": [ingredient_display_name(i.name, language) for i in recipe.ingredients],
        }
        for recipe in recipes.all()
    ]
    items.sort(key=lambda item: fold(item["short_name"]))
    return items
