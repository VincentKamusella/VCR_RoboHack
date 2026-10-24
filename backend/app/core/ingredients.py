"""Resolves ingredient words (English or German) to ingredient names in the database."""
from __future__ import annotations

from dataclasses import dataclass
from difflib import get_close_matches

from . import lexicon
from .parser import content_words
from .text import Token

MAX_PHRASE_WORDS = 4
FUZZY_PHRASE_CUTOFF = 0.84


@dataclass(frozen=True)
class ResolvedTerm:
    text: str                 # the words as the user typed them
    names: frozenset[str]     # matching ingredient names in the database
    exact: str | None = None  # set when the words are one ingredient's own name ("Onion")


def ingredient_display_name(name: str, language: str) -> str:
    """'Pineapple' -> 'Ananas' in German; English names are the database names."""
    if language == "de" and name in lexicon.INGREDIENTS:
        return lexicon.INGREDIENTS[name][0]
    return name


class IngredientResolver:
    def __init__(self, ingredient_categories: dict[str, str]):
        self.categories = ingredient_categories
        self.terms: dict[str, set[str]] = {}

        # An ingredient's own name (English or German display name) refers to exactly that
        # ingredient, even where the same word is also a group ("Onion" vs. "onions").
        self.exact: dict[str, str] = {}
        for name in ingredient_categories:
            self._add(name, [name])
            self.exact[" ".join(content_words(name))] = name
        for name, (german, synonyms) in lexicon.INGREDIENTS.items():
            if name in ingredient_categories:
                self.exact.setdefault(" ".join(content_words(german)), name)
                for term in [german, *synonyms]:
                    self._add(term, [name])
        for term, names in lexicon.INGREDIENT_GROUPS.items():
            self._add(term, [n for n in names if n in ingredient_categories])
        for term, category in lexicon.CATEGORY_WORDS.items():
            self._add(term, [n for n, c in ingredient_categories.items() if c == category])

        self.vocabulary = {w for term in self.terms for w in term.split()}
        self._term_list = list(self.terms)

    def _add(self, text: str, names: list[str]) -> None:
        key = " ".join(content_words(text))
        if key and names:
            self.terms.setdefault(key, set()).update(names)

    def resolve(self, tokens: list[Token]) -> tuple[list[ResolvedTerm], list[str]]:
        """Split a run of words into known ingredient terms, longest match first.

        Returns the resolved terms and the leftover words that are not ingredients.
        """
        resolved: list[ResolvedTerm] = []
        unknown: list[str] = []
        pending_unknown: list[str] = []
        i = 0
        while i < len(tokens):
            hit = self._lookup(tokens, i)
            if hit:
                size, names, exact = hit
                if pending_unknown:
                    unknown.append(" ".join(pending_unknown))
                    pending_unknown = []
                text = " ".join(t.raw for t in tokens[i:i + size])
                resolved.append(ResolvedTerm(text, frozenset(names), exact))
                i += size
            else:
                pending_unknown.append(tokens[i].raw)
                i += 1
        if pending_unknown:
            unknown.append(" ".join(pending_unknown))
        return resolved, unknown

    def _lookup(self, tokens: list[Token], i: int) -> tuple[int, set[str], str | None] | None:
        longest = min(MAX_PHRASE_WORDS, len(tokens) - i)
        for size in range(longest, 0, -1):
            phrase = " ".join(t.norm for t in tokens[i:i + size])
            if phrase in self.terms:
                return size, self.terms[phrase], self.exact.get(phrase)
        for size in range(min(3, longest), 0, -1):
            phrase = " ".join(t.norm for t in tokens[i:i + size])
            if len(phrase) < 4:
                continue
            close = get_close_matches(phrase, self._term_list, n=1, cutoff=FUZZY_PHRASE_CUTOFF)
            if close:
                return size, self.terms[close[0]], self.exact.get(close[0])
        return None

    def display_name(self, name: str, language: str) -> str:
        return ingredient_display_name(name, language)
