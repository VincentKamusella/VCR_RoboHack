"""Matches the pizza words of a message against recipe names and aliases."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from ..data.recipes import Recipe
from . import lexicon
from .parser import STOPWORDS, content_words
from .text import Token, fold, similarity

AMBIGUITY_MARGIN = 0.03
MAX_CANDIDATES = 5


class MatchKind(str, Enum):
    EXACT = "exact"          # one pizza clearly named
    AMBIGUOUS = "ambiguous"  # several pizzas fit equally well -> ask which one
    PARTIAL = "partial"      # only part of a name matched -> suggest and confirm
    NONE = "none"            # nothing on the menu fits


@dataclass
class PizzaMatch:
    kind: MatchKind
    candidates: list[Recipe] = field(default_factory=list)
    window: tuple[int, int] | None = None  # token positions (in pizza_tokens) of the matched name
    from_partial: bool = False             # True when only part of a name matched

    @property
    def recipe(self) -> Recipe | None:
        return self.candidates[0] if self.kind == MatchKind.EXACT else None


class PizzaMatcher:
    def __init__(self, recipes: list[Recipe]):
        self.recipes = {r.name: r for r in recipes}
        self.phrases: list[tuple[tuple[str, ...], Recipe]] = []
        for recipe in recipes:
            self._add(recipe.name, recipe)
            for alias in lexicon.PIZZA_ALIASES.get(recipe.name, []):
                self._add(alias, recipe)
        self.vocabulary = {w for phrase, _ in self.phrases for w in phrase}

    def _add(self, text: str, recipe: Recipe) -> None:
        phrase = tuple(content_words(text))
        if phrase:
            self.phrases.append((phrase, recipe))

    def match(self, tokens: list[Token], restrict_to: list[str] | None = None,
              alternatives: bool = True) -> PizzaMatch:
        """Find the best pizza for the given pizza words.

        Longer names win ('salami funghi' beats 'salami'); ties become AMBIGUOUS.
        `restrict_to` limits the search to some pizza names (used while clarifying).
        With `alternatives=False`, a tie between pizzas named at different places goes to the
        first one ("Margherita with ham" is a Margherita, not a Prosciutto).
        """
        norms = [t.norm for t in tokens if t.norm not in STOPWORDS]
        if not norms:
            return PizzaMatch(MatchKind.NONE)

        best: dict[str, tuple[int, float, tuple[int, int]]] = {}
        for phrase, recipe in self.phrases:
            if restrict_to is not None and recipe.name not in restrict_to:
                continue
            size = len(phrase)
            for start in range(len(norms) - size + 1):
                sims = [similarity(norms[start + k], phrase[k]) for k in range(size)]
                if all(sims):
                    score = (size, sum(sims) / size, (start, start + size))
                    if recipe.name not in best or score[:2] > best[recipe.name][:2]:
                        best[recipe.name] = score

        if best:
            top = max(best.values(), key=lambda s: s[:2])
            tied = [
                name for name, s in best.items()
                if s[0] == top[0] and s[1] >= top[1] - AMBIGUITY_MARGIN
            ]
            tied.sort(key=lambda n: -best[n][1])
            if len(tied) > 1 and not alternatives:
                starts = sorted(best[n][2][0] for n in tied)
                if starts[0] < starts[1]:
                    tied = [n for n in tied if best[n][2][0] == starts[0]]
            if len(tied) == 1:
                return PizzaMatch(MatchKind.EXACT, [self.recipes[tied[0]]], best[tied[0]][2])
            return PizzaMatch(MatchKind.AMBIGUOUS, [self.recipes[n] for n in tied[:MAX_CANDIDATES]])

        # No full name matched: look for pizzas sharing a distinctive word ("quattro", "goat").
        partial: dict[str, float] = {}
        for phrase, recipe in self.phrases:
            if restrict_to is not None and recipe.name not in restrict_to:
                continue
            for word in phrase:
                if len(word) < 4:
                    continue
                for n in norms:
                    sim = similarity(n, word)
                    if sim:
                        partial[recipe.name] = max(partial.get(recipe.name, 0), sim)
        if not partial:
            return PizzaMatch(MatchKind.NONE)
        names = sorted(partial, key=lambda n: -partial[n])[:MAX_CANDIDATES]
        kind = MatchKind.PARTIAL if len(names) == 1 else MatchKind.AMBIGUOUS
        return PizzaMatch(kind, [self.recipes[n] for n in names], from_partial=True)

    def find_by_name(self, text: str) -> Recipe | None:
        target = fold(text)
        return next((r for r in self.recipes.values() if fold(r.name) == target), None)
