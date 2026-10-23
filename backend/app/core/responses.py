"""Everything the bot says, in English and German."""
from __future__ import annotations

from .text import join_list

TEXTS = {
    "en": {
        "greeting": "Hi! 🍕 What kind of pizza would you like? (Deutsch geht auch!)",
        "order_ok": "Great choice: {pizza}{without}. Your order is noted! 🍕",
        "without": " without {items}",
        "not_on_pizza": "By the way, {pizza} doesn't come with {items} anyway.",
        "unknown_ingredient": "I don't know {items} as an ingredient, so I ignored that.",
        "no_additions": "I can only leave ingredients out, not add extras, so {items} won't be added.",
        "another": "Would you like another pizza? Just tell me which one.",
        "not_found": "Sorry, we don't have “{requested}” on our menu. I've noted it as a wish for the future. 📝",
        "not_found_suggest": "Sorry, we don't have “{requested}” on our menu. I've noted it as a wish for the future. 📝 We do have {pizza}. Would you like that instead?",
        "ask_other": "Which other pizza would you like?",
        "ambiguous": "Did you mean {options}? Answer with the name or the number.",
        "partial": "Did you mean {pizza}?",
        "clarify_again": "Sorry, I didn't get that. Please pick one: {options}.",
        "not_understood": "I didn't catch which pizza you'd like. Try something like “Margherita” or “Hawaii without pineapple”.",
        "exclusions_only": "Which pizza should I leave {items} off?",
        "menu": "Here is our menu: {names}. Which one would you like?",
        "cancelled": "No problem. Which pizza would you like instead?",
        "too_long": "That's a bit long for me. Please just tell me the pizza you'd like.",
        "greet_back": "Hi! 🍕 What kind of pizza would you like?",
        "goodbye": "Alright, enjoy your meal! If you want another pizza, just name it.",
        "and": "and",
        "or": "or",
    },
    "de": {
        "greeting": "Hallo! 🍕 Welche Pizza darf es sein? (English works too!)",
        "order_ok": "Gute Wahl: {pizza}{without}. Deine Bestellung ist notiert! 🍕",
        "without": " ohne {items}",
        "not_on_pizza": "Übrigens: Auf der {pizza} sind sowieso keine {items}.",
        "unknown_ingredient": "{items} kenne ich nicht als Zutat, das habe ich ignoriert.",
        "no_additions": "Ich kann Zutaten nur weglassen, nicht hinzufügen. {items} kommt also nicht extra drauf.",
        "another": "Möchtest du noch eine Pizza? Sag mir einfach welche.",
        "not_found": "Leider haben wir „{requested}“ nicht auf der Karte. Ich habe es mir als Wunsch für später notiert. 📝",
        "not_found_suggest": "Leider haben wir „{requested}“ nicht auf der Karte. Ich habe es mir als Wunsch für später notiert. 📝 Wir haben aber die {pizza}. Möchtest du die stattdessen?",
        "ask_other": "Welche andere Pizza möchtest du?",
        "ambiguous": "Meinst du {options}? Antworte mit dem Namen oder der Nummer.",
        "partial": "Meinst du die {pizza}?",
        "clarify_again": "Das habe ich nicht verstanden. Bitte wähle eine: {options}.",
        "not_understood": "Ich habe nicht verstanden, welche Pizza du möchtest. Probier zum Beispiel „Margherita“ oder „Hawaii ohne Ananas“.",
        "exclusions_only": "Bei welcher Pizza soll ich {items} weglassen?",
        "menu": "Das ist unsere Karte: {names}. Welche möchtest du?",
        "cancelled": "Kein Problem. Welche Pizza möchtest du stattdessen?",
        "too_long": "Das ist mir etwas zu lang. Sag mir einfach, welche Pizza du möchtest.",
        "greet_back": "Hallo! 🍕 Welche Pizza darf es sein?",
        "goodbye": "Alles klar, guten Appetit! Wenn du noch eine Pizza möchtest, nenn sie einfach.",
        "and": "und",
        "or": "oder",
    },
}

SUGGESTIONS = {
    "en": ["Margherita", "Hawaii without pineapple", "Show the menu"],
    "de": ["Margherita", "Salami ohne Zwiebeln", "Speisekarte zeigen"],
}


def say(lang: str, key: str, **kwargs) -> str:
    return TEXTS.get(lang, TEXTS["en"])[key].format(**kwargs)


def items(lang: str, values: list[str], conjunction: str = "and") -> str:
    return join_list(values, TEXTS.get(lang, TEXTS["en"])[conjunction])


def numbered_options(lang: str, names: list[str]) -> str:
    return items(lang, [f"{i}) {n}" for i, n in enumerate(names, 1)], "or")
