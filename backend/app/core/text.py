"""Low-level text helpers: folding, tokenizing and fuzzy token comparison."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

_TOKEN_RE = re.compile(r"[^\W_]+|[,.;!?&]")
PUNCTUATION = {",", ".", ";", "!", "?"}


def fold(text: str) -> str:
    """Lowercase and strip accents so 'Döner', 'doner' and 'DÖNER' compare equal.

    'ß' becomes 'ss' and umlauts lose their dots ('Käse' -> 'kase').
    """
    text = text.lower().replace("ß", "ss")
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


@dataclass(frozen=True)
class Token:
    raw: str      # exactly as typed
    norm: str     # folded form used for matching
    index: int    # position in the token list
    start: int    # character offsets in the original message
    end: int

    @property
    def is_punct(self) -> bool:
        return self.norm in PUNCTUATION


def tokenize(text: str) -> list[Token]:
    tokens = []
    for i, m in enumerate(_TOKEN_RE.finditer(text)):
        raw = m.group(0)
        norm = "and" if raw == "&" else fold(raw)
        tokens.append(Token(raw=raw, norm=norm, index=i, start=m.start(), end=m.end()))
    return tokens


def words(text: str) -> list[str]:
    """Folded word tokens without punctuation."""
    return [t.norm for t in tokenize(text) if not t.is_punct]


def similarity(a: str, b: str) -> float:
    """1.0 for identical tokens, the fuzzy ratio for similar long tokens, else 0.

    Short tokens (< 4 letters) must match exactly, otherwise 'ham' would match 'hot'.
    """
    if a == b:
        return 1.0
    if min(len(a), len(b)) < 4:
        return 0.0
    ratio = SequenceMatcher(None, a, b).ratio()
    return ratio if ratio >= FUZZY_TOKEN_THRESHOLD else 0.0


FUZZY_TOKEN_THRESHOLD = 0.82


def join_list(items: list[str], conjunction: str) -> str:
    """['a', 'b', 'c'] -> 'a, b and c'."""
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    return f"{', '.join(items[:-1])} {conjunction} {items[-1]}"
