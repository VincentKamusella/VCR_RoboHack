"""The conversation logic: decides what to do with each user message.

The engine returns a `Reply`. Only `text` and `suggestions` are meant for the user;
`order` and `missing` are internal and never leave the backend through the chat API.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from ..data.recipes import Recipe, RecipeRepository
from ..data.state_store import now_iso
from ..services.order_sink import OrderSink
from ..services.wishlist import Wishlist
from . import responses as r
from .custom import CUSTOM_NAME, find_trigger, resolve_toppings, topping_tokens
from .ingredients import IngredientResolver
from .matcher import MatchKind, PizzaMatch, PizzaMatcher
from .parser import (
    BYE, CANCEL, GREETINGS, MENU, NO, POSTFIX_MARKERS, PREFIX_MARKERS, STOPWORDS, YES, ParsedMessage, parse,
)
from .session import DialogState, Session
from .text import Token

MAX_MESSAGE_TOKENS = 60
MAX_WISH_WORDS = 6
DOUGH = "standard pizza dough"
YES_NO = {"en": ["Yes", "No"], "de": ["Ja", "Nein"]}
INTENT_WORDS = YES | NO | CANCEL | MENU | GREETINGS | BYE


@dataclass
class Reply:
    text: str
    suggestions: list[str] = field(default_factory=list)
    order: dict | None = None      # internal: the matched recipe, already sent to the order sink
    missing: str | None = None     # internal: pizza name pinned to the wishlist


class DialogEngine:
    def __init__(self, recipes: RecipeRepository, order_sink: OrderSink, wishlist: Wishlist):
        self.recipes = recipes
        self.order_sink = order_sink
        self.wishlist = wishlist
        self.matcher = PizzaMatcher(recipes.all())
        self.resolver = IngredientResolver(recipes.ingredient_categories())
        self.known_words = (
            self.matcher.vocabulary | self.resolver.vocabulary | STOPWORDS
            | PREFIX_MARKERS | POSTFIX_MARKERS | YES | NO | CANCEL | MENU
        )

    # --- entry points ---------------------------------------------------------------

    def greet(self, session: Session) -> Reply:
        lang = session.language
        return Reply(r.say(lang, "greeting"), r.SUGGESTIONS[lang])

    def set_language(self, session: Session, language: str) -> Reply:
        """The user picked a language in the UI: switch, drop any open question, greet again."""
        session.reset_pending()
        session.language = language
        session.language_locked = True
        return self.greet(session)

    def handle(self, session: Session, text: str, original: str | None = None) -> Reply:
        """Process one message. `original` is the user's own wording when `text` is a
        normalized request built by the agent (e.g. "Pizza Hawaii without pineapple")."""
        text = (text or "").strip()
        msg = parse(text)
        if original:
            msg.original = original
        if msg.language and not session.language_locked:
            session.language = msg.language
        lang = session.language

        if not msg.tokens:
            return Reply(r.say(lang, "not_understood"), r.SUGGESTIONS[lang])
        if len(msg.tokens) > MAX_MESSAGE_TOKENS:
            return Reply(r.say(lang, "too_long"))
        if msg.wants_cancel:
            session.reset_pending()
            return Reply(r.say(lang, "cancelled"), r.SUGGESTIONS[lang])
        start = find_trigger(msg)
        if start is not None:
            return self._custom(session, msg, topping_tokens(msg, start))
        if session.state == DialogState.CUSTOMIZING:
            chunks = topping_tokens(msg, 0)
            request = resolve_toppings(chunks, self.resolver, self.recipes.ingredient_categories())
            if request.toppings or request.vague:
                return self._custom(session, msg, chunks)
            session.reset_pending()   # not toppings after all: handle it as a normal message
        if session.state == DialogState.CLARIFYING:
            return self._clarify(session, msg)
        return self._choose(session, msg)

    # --- custom pizza -----------------------------------------------------------------

    def _custom(self, session: Session, msg: ParsedMessage, chunks: list[list[Token]]) -> Reply:
        lang = session.language
        categories = self.recipes.ingredient_categories()
        request = resolve_toppings(chunks, self.resolver, categories)
        notes = []
        if request.vague:
            notes.append(r.say(lang, "custom_vague", items=r.items(lang, [f"“{v}”" for v in request.vague])))
        if request.unknown:
            notes.append(r.say(lang, "unknown_ingredient", items=r.items(lang, [f"“{u}”" for u in request.unknown])))

        if not request.toppings:
            session.reset_pending()
            session.state = DialogState.CUSTOMIZING
            session.pending_message = msg.original
            return Reply(" ".join([*notes, r.say(lang, "custom_ask")]))

        order = self._new_order(session, msg.original, msg.text)
        order.update({
            "pizza": {"id": None, "slug": "custom-pizza", "name": CUSTOM_NAME,
                      "style": "Custom", "origin": "Custom", "custom": True},
            "ingredients": [{"name": n, "category": categories[n]} for n in request.toppings],
            "removed_ingredients": [],
            "ignored": {"not_on_pizza": [], "unknown": request.unknown, "additions": [], "vague": request.vague},
        })
        self.order_sink.submit(order)
        session.reset_pending()
        shown = [self.resolver.display_name(n, lang) for n in request.toppings]
        text = r.say(lang, "custom_ok", pizza=r.say(lang, "custom_name"), items=r.items(lang, shown))
        return Reply(" ".join([text, *notes, r.say(lang, "another")]), order=order)

    def _new_order(self, session: Session, message: str, interpreted: str | None) -> dict:
        """The fields every order shares."""
        return {
            "order_id": uuid.uuid4().hex,
            "created_at": now_iso(),
            "session_id": session.id,
            "language": session.language,
            "message": message,
            "interpreted_as": interpreted or message,
            "base": DOUGH,
        }

    # --- awaiting a pizza -----------------------------------------------------------

    def _choose(self, session: Session, msg: ParsedMessage) -> Reply:
        lang = session.language
        match = self.matcher.match(msg.pizza_tokens, alternatives=msg.offers_alternatives)

        if match.kind == MatchKind.EXACT:
            recipe = match.recipe
            unknown = self._unknown_neighbours(msg, match)
            if unknown:
                # "Chicken Tikka": the name is longer than anything we have -> not on the menu.
                span = sorted(unknown + msg.pizza_tokens[match.window[0]:match.window[1]], key=lambda t: t.index)
                requested = self._span(msg, span)
                self._pin(requested, span, msg, lang)
                self._ask(session, msg, [recipe.name])
                return Reply(
                    r.say(lang, "not_found_suggest", requested=requested, pizza=recipe.name),
                    YES_NO[lang], missing=requested,
                )
            window = match.window
            leftover = msg.pizza_tokens[:window[0]] + msg.pizza_tokens[window[1]:]
            return self._finalize(session, recipe, msg.exclusion_chunks, leftover, msg.original, msg.text)

        if match.kind in (MatchKind.AMBIGUOUS, MatchKind.PARTIAL):
            names = [c.name for c in match.candidates]
            self._ask(session, msg, names)
            if match.from_partial:
                content = self._content(msg)
                session.pending_wish = (self._span(msg, content), " ".join(t.norm for t in content))
            if match.kind == MatchKind.PARTIAL:
                return Reply(r.say(lang, "partial", pizza=names[0]), YES_NO[lang])
            return Reply(r.say(lang, "ambiguous", options=r.numbered_options(lang, names)), names)

        # Nothing on the menu matches.
        if msg.wants_menu:
            return self._menu(lang)
        content = self._content(msg)
        if not content or all(t.norm in INTENT_WORDS for t in content):
            if msg.exclusion_chunks:
                excluded = [t.raw for chunk in msg.exclusion_chunks for t in chunk]
                return Reply(r.say(lang, "exclusions_only", items=r.items(lang, excluded)))
            if msg.says_no or msg.says_bye:
                return Reply(r.say(lang, "goodbye"))
            if msg.greets:
                return Reply(r.say(lang, "greet_back"), r.SUGGESTIONS[lang])
            return Reply(r.say(lang, "not_understood"), r.SUGGESTIONS[lang])
        if len(content) > MAX_WISH_WORDS:
            return Reply(r.say(lang, "not_understood"), r.SUGGESTIONS[lang])
        requested = self._span(msg, content)
        self._pin(requested, content, msg, lang)
        return Reply(
            f"{r.say(lang, 'not_found', requested=requested)} {r.say(lang, 'ask_other')}",
            r.SUGGESTIONS[lang], missing=requested,
        )

    # --- answering a "did you mean ...?" question -----------------------------------

    def _clarify(self, session: Session, msg: ParsedMessage) -> Reply:
        lang = session.language
        candidates = session.candidates

        chosen: str | None = None
        restricted = self.matcher.match(msg.pizza_tokens, restrict_to=candidates)
        if restricted.kind in (MatchKind.EXACT, MatchKind.PARTIAL):
            chosen = restricted.candidates[0].name
        elif msg.ordinal is not None and msg.ordinal < len(candidates):
            chosen = candidates[msg.ordinal]
        elif msg.says_yes and len(candidates) == 1:
            chosen = candidates[0]

        if chosen:
            recipe = self.recipes.get(chosen)
            exclusions = session.pending_exclusions + msg.exclusion_chunks
            message = f"{session.pending_message} | {msg.original}"
            return self._finalize(session, recipe, exclusions, [], message, msg.text)

        # The user named a different pizza: start over with this message.
        if msg.pizza_tokens and self.matcher.match(msg.pizza_tokens, alternatives=msg.offers_alternatives).kind != MatchKind.NONE:
            self._decline(session)
            return self._choose(session, msg)

        if msg.says_no:
            missing = self._decline(session)
            if missing:
                text = f"{r.say(lang, 'not_found', requested=missing)} {r.say(lang, 'ask_other')}"
                return Reply(text, r.SUGGESTIONS[lang], missing=missing)
            return Reply(r.say(lang, "ask_other"), r.SUGGESTIONS[lang])

        # Something new that matches nothing: treat it as a fresh request.
        if self._content(msg) and not msg.says_yes:
            self._decline(session)
            return self._choose(session, msg)

        options = r.numbered_options(lang, candidates)
        suggestions = YES_NO[lang] if len(candidates) == 1 else candidates
        return Reply(r.say(lang, "clarify_again", options=options), suggestions)

    # --- helpers --------------------------------------------------------------------

    def _finalize(self, session: Session, recipe: Recipe, exclusion_chunks: list[list[Token]],
                  leftover: list[Token], message: str, interpreted: str | None = None) -> Reply:
        lang = session.language
        recipe_names = [i.name for i in recipe.ingredients]

        removed: list[str] = []
        not_on_pizza: list[str] = []
        unknown: list[str] = []
        for chunk in exclusion_chunks:
            terms, unresolved = self.resolver.resolve(chunk)
            unknown.extend(unresolved)
            for term in terms:
                hits = [n for n in recipe_names if n in term.names]
                if term.exact in hits:
                    hits = [term.exact]   # "without Onion" keeps the Red Onion
                if hits:
                    removed.extend(n for n in hits if n not in removed)
                else:
                    not_on_pizza.append(term.text)

        additions: list[str] = []
        if leftover:
            terms, _ = self.resolver.resolve(leftover)
            additions = [t.text for t in terms if not (t.names & set(recipe_names))]

        order = self._new_order(session, message, interpreted)
        order.update({
            "pizza": {
                "id": recipe.id, "slug": recipe.slug, "name": recipe.name,
                "style": recipe.style, "origin": recipe.origin,
            },
            "ingredients": [
                {"name": i.name, "category": i.category}
                for i in recipe.ingredients if i.name not in removed
            ],
            "removed_ingredients": removed,
            "ignored": {"not_on_pizza": not_on_pizza, "unknown": unknown, "additions": additions},
        })
        self.order_sink.submit(order)
        session.reset_pending()

        without = ""
        if removed:
            shown = [self.resolver.display_name(n, lang) for n in removed]
            without = r.say(lang, "without", items=r.items(lang, shown))
        parts = [r.say(lang, "order_ok", pizza=recipe.name, without=without)]
        if not_on_pizza:
            parts.append(r.say(lang, "not_on_pizza", pizza=recipe.name, items=r.items(lang, not_on_pizza)))
        if unknown:
            parts.append(r.say(lang, "unknown_ingredient", items=r.items(lang, [f"“{u}”" for u in unknown])))
        if additions:
            parts.append(r.say(lang, "no_additions", items=r.items(lang, additions)))
        parts.append(r.say(lang, "another"))
        return Reply(" ".join(parts), order=order)

    def _ask(self, session: Session, msg: ParsedMessage, names: list[str]) -> None:
        session.state = DialogState.CLARIFYING
        session.candidates = names
        session.pending_exclusions = msg.exclusion_chunks
        session.pending_message = msg.original
        session.pending_wish = None

    def _decline(self, session: Session) -> str | None:
        """The user rejected our suggestion. Pin their original wording if it was not on the menu."""
        wish = session.pending_wish
        message = session.pending_message
        language = session.language
        session.reset_pending()
        if wish:
            requested, normalized = wish
            self.wishlist.add(requested, normalized, message, language)
            return requested
        return None

    def _pin(self, requested: str, tokens: list[Token], msg: ParsedMessage, lang: str) -> None:
        normalized = " ".join(t.norm for t in tokens if t.norm not in STOPWORDS)
        self.wishlist.add(requested, normalized, msg.original, lang)

    def _unknown_neighbours(self, msg: ParsedMessage, match: PizzaMatch) -> list[Token]:
        """Unknown words written directly before or after the matched pizza name."""
        start, end = match.window
        in_pizza_part = {t.index for t in msg.pizza_tokens}
        found: list[Token] = []
        for step, edge in ((-1, msg.pizza_tokens[start].index), (1, msg.pizza_tokens[end - 1].index)):
            i = edge + step
            while 0 <= i < len(msg.tokens):
                tok = msg.tokens[i]
                if (tok.is_punct or i not in in_pizza_part or tok.norm.isdigit()
                        or tok.norm in self.known_words):
                    break
                found.append(tok)
                i += step
        return found

    @staticmethod
    def _content(msg: ParsedMessage) -> list[Token]:
        return [t for t in msg.pizza_tokens if not t.norm.isdigit()]

    @staticmethod
    def _span(msg: ParsedMessage, tokens: list[Token]) -> str:
        """The user's own wording from the first to the last of the given tokens."""
        first = min(tokens, key=lambda t: t.start)
        last = max(tokens, key=lambda t: t.end)
        return msg.text[first.start:last.end]

    def _menu(self, lang: str) -> Reply:
        names = sorted(rec.name for rec in self.recipes.all())
        return Reply(r.say(lang, "menu", names=", ".join(names)))
