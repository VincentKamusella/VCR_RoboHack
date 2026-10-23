"""Turns a raw chat message into structured parts: pizza words, exclusions and intents.

Example: "Ich hätte gerne eine Hawaii ohne Ananas, bitte"
  pizza_tokens     -> [hawaii]
  exclusion_chunks -> [[ananas]]
  language         -> "de"
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import lexicon
from .text import Token, fold, tokenize, words


def _folded_set(*sources: str) -> frozenset[str]:
    out: set[str] = set()
    for source in sources:
        out.update(words(source))
    return frozenset(out)


STOPWORDS = _folded_set(lexicon.STOPWORDS_EN, lexicon.STOPWORDS_DE, lexicon.STOPWORDS_IT)
PREFIX_MARKERS = _folded_set(lexicon.EXCLUSION_PREFIX)
POSTFIX_MARKERS = _folded_set(lexicon.EXCLUSION_POSTFIX)
TERMINATORS = _folded_set(lexicon.EXCLUSION_TERMINATORS)
SEPARATORS = _folded_set(lexicon.LIST_SEPARATORS)
BOUNDARIES = _folded_set(lexicon.CLAUSE_BOUNDARIES)
YES = _folded_set(lexicon.YES_WORDS)
NO = _folded_set(lexicon.NO_WORDS)
CANCEL = _folded_set(lexicon.CANCEL_WORDS)
GREETINGS = _folded_set(lexicon.GREETING_WORDS)
ALTERNATIVES = _folded_set(lexicon.ALTERNATIVE_WORDS)
MENU = _folded_set(lexicon.MENU_WORDS)
MENU_PHRASES = [" ".join(words(p)) for p in lexicon.MENU_PHRASES]
GERMAN_HINTS = _folded_set(lexicon.GERMAN_HINTS)
ENGLISH_HINTS = _folded_set(lexicon.ENGLISH_HINTS)
ORDINALS = {fold(k): v for k, v in lexicon.ORDINALS.items()}


def content_words(text: str) -> list[str]:
    """Folded words of a name or alias without stopwords ('Pizza Salami e Funghi' -> [salami, funghi])."""
    return [w for w in words(text) if w not in STOPWORDS]


@dataclass
class ParsedMessage:
    text: str
    tokens: list[Token]
    pizza_tokens: list[Token] = field(default_factory=list)
    exclusion_chunks: list[list[Token]] = field(default_factory=list)
    language: str | None = None
    wants_menu: bool = False
    says_yes: bool = False
    says_no: bool = False
    wants_cancel: bool = False
    greets: bool = False
    offers_alternatives: bool = False   # "Salami OR Margherita"
    ordinal: int | None = None

    @property
    def is_empty(self) -> bool:
        return not self.pizza_tokens and not self.exclusion_chunks


def detect_language(tokens: list[Token], text: str) -> str | None:
    norms = [t.norm for t in tokens]
    de = sum(n in GERMAN_HINTS for n in norms) + sum(c in "äöüßÄÖÜ" for c in text)
    en = sum(n in ENGLISH_HINTS for n in norms)
    if de > en:
        return "de"
    if en > de:
        return "en"
    return None


def parse(text: str) -> ParsedMessage:
    tokens = tokenize(text)
    msg = ParsedMessage(text=text, tokens=tokens)
    _split_exclusions(msg)
    _detect_intents(msg)
    msg.language = detect_language(tokens, text)
    return msg


def _split_exclusions(msg: ParsedMessage) -> None:
    tokens = msg.tokens
    pizza: list[Token] = []
    chunks: list[list[Token]] = []
    current: list[Token] = []
    in_scope = False
    last_boundary = -1

    def flush() -> None:
        nonlocal current
        kept = [t for t in current if t.norm not in STOPWORDS]
        if kept:
            chunks.append(kept)
        current = []

    for i, tok in enumerate(tokens):
        n = tok.norm
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None

        if n in PREFIX_MARKERS:
            # "No, a Funghi please": a marker followed by punctuation is just an answer.
            if nxt is None or nxt.is_punct:
                continue
            flush()
            in_scope = True
            continue

        if n in POSTFIX_MARKERS:
            if in_scope:
                flush()
                in_scope = False
            else:
                moved = [t for t in pizza if t.index > last_boundary]
                pizza = [t for t in pizza if t.index <= last_boundary]
                if moved:
                    chunks.append(moved)
            last_boundary = i
            continue

        if in_scope:
            if (tok.is_punct and n != ",") or n in TERMINATORS:
                flush()
                in_scope = False
                last_boundary = i
            elif n == "," or n in SEPARATORS:
                flush()
            else:
                current.append(tok)
            continue

        if tok.is_punct or n in BOUNDARIES:
            last_boundary = i
        if not tok.is_punct and n not in STOPWORDS:
            pizza.append(tok)

    flush()
    msg.pizza_tokens = pizza
    msg.exclusion_chunks = chunks


def _detect_intents(msg: ParsedMessage) -> None:
    norms = [t.norm for t in msg.tokens if not t.is_punct]
    joined = " ".join(norms)
    norm_set = set(norms)
    msg.wants_menu = bool(norm_set & MENU) or any(p in joined for p in MENU_PHRASES)
    msg.says_yes = bool(norm_set & YES) and len(norms) <= 4
    msg.says_no = bool(norm_set & NO) and not msg.exclusion_chunks
    msg.wants_cancel = bool(norm_set & CANCEL) and len(norms) <= 4
    msg.greets = bool(norm_set & GREETINGS)
    msg.offers_alternatives = bool(norm_set & ALTERNATIVES)
    for n in norms:
        if n in ORDINALS:
            msg.ordinal = ORDINALS[n]
            break
