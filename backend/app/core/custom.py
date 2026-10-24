"""Custom pizza: the customer picks any toppings from the ingredients in the database.

Recognized requests look like "Custom Pizza with Mozzarella, Salami and Mushrooms" (sent by the
menu book) or free text such as "I want to build my own pizza with ham and corn" or
"Eigene Pizza mit Thunfisch und Mais".
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import lexicon
from .ingredients import IngredientResolver
from .parser import PREFIX_MARKERS, SEPARATORS, STOPWORDS, ParsedMessage
from .text import Token, words

CUSTOM_NAME = "Custom Pizza"   # name used in orders, independent of the chat language
TRIGGERS = sorted((tuple(words(p)) for p in lexicon.CUSTOM_PIZZA_PHRASES), key=len, reverse=True)
LEAD_WORDS = {"with", "mit", "and", "und", "please", "bitte", "toppings", "topping", "belag", "belegt", "auf"}
MAX_NAMES_FOR_ONE_TERM = 1


@dataclass
class CustomRequest:
    toppings: list[str] = field(default_factory=list)   # ingredient names from the database
    vague: list[str] = field(default_factory=list)      # words that fit several ingredients ("cheese")
    unknown: list[str] = field(default_factory=list)    # words that are no ingredient at all


def find_trigger(msg: ParsedMessage) -> int | None:
    """Index of the first token after "custom pizza" / "eigene Pizza" / "build my own", or None."""
    norms = [t.norm for t in msg.tokens]
    for start in range(len(norms)):
        for trigger in TRIGGERS:
            end = start + len(trigger)
            if tuple(norms[start:end]) == trigger:
                # "build my own pizza": also skip a trailing "pizza".
                while end < len(norms) and norms[end] in ("pizza", "pie"):
                    end += 1
                return end
    return None


def topping_tokens(msg: ParsedMessage, start: int) -> list[list[Token]]:
    """Toppings listed after the trigger, split into chunks. Stops at an exclusion word."""
    chunks: list[list[Token]] = []
    current: list[Token] = []
    for tok in msg.tokens[start:]:
        n = tok.norm
        if n in PREFIX_MARKERS or (tok.is_punct and n != ","):
            break
        if n == "," or n in SEPARATORS:
            if current:
                chunks.append(current)
            current = []
        elif n not in STOPWORDS and n not in LEAD_WORDS:
            current.append(tok)
    if current:
        chunks.append(current)
    return chunks


def resolve_toppings(chunks: list[list[Token]], resolver: IngredientResolver,
                     categories: dict[str, str]) -> CustomRequest:
    request = CustomRequest()
    for chunk in chunks:
        terms, unknown = resolver.resolve(chunk)
        request.unknown.extend(unknown)
        for term in terms:
            if term.exact:
                names = [term.exact]
            elif len(term.names) <= MAX_NAMES_FOR_ONE_TERM:
                names = list(term.names)
            else:
                request.vague.append(term.text)
                continue
            for name in names:
                if name in categories and name not in request.toppings:
                    request.toppings.append(name)
    return request
