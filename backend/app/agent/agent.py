"""The conversational agent: llama understands and talks, the rule engine decides.

For every customer message:
  1. The LLM extracts intent, pizza and excluded ingredients as JSON.
  2. That extraction is checked against the customer's own words ("grounding"), so the model
     cannot order a pizza or drop an ingredient the customer never mentioned.
  3. A normalized request such as "Pizza Hawaii without pineapple" goes through the existing
     DialogEngine, which matches the database, hands orders to the order sink and pins wishes.
  4. The LLM rewrites the engine's reply in a friendly tone. The rewrite is checked to still
     contain the key facts; otherwise the engine's own text is used.

If the LLM is unreachable or misbehaves, the engine handles the message exactly as before.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from ..core import responses as r
from ..core.custom import find_trigger
from ..core.dialog import DialogEngine, Reply
from ..core.ingredients import ingredient_display_name
from ..core.matcher import MatchKind
from ..core.parser import (
    BYE, CANCEL, GREETINGS, NO, ORDINALS, STOPWORDS, YES, ParsedMessage, content_words, detect_language, parse,
)
from ..core.session import DialogState, Session
from ..core.text import fold, similarity, tokenize, words
from ..services.menu import short_name
from . import prompts
from .llm import LLMClient, LLMError

log = logging.getLogger("pizzabot.agent")

HISTORY_TURNS = 12
SMALL_TALK = YES | NO | BYE | GREETINGS | CANCEL
MAX_REPLY_CHARS = 600
BASE_INGREDIENTS = {"Tomato Sauce", "Mozzarella"}
PLACEHOLDERS = {"", "none", "nothing", "n a", "na", "null", "no", "keine", "nichts", "none mentioned"}
CLAIMS_ORDER = ["your order", "order is", "i've noted", "i have noted", "noted your", "order has been",
                "bestellung ist", "notiert", "ist bestellt", "habe ich bestellt"]
WORDS = {"en": {"without": "without", "yes": "yes", "no": "no", "menu": "menu", "cancel": "cancel"},
         "de": {"without": "ohne", "yes": "ja", "no": "nein", "menu": "speisekarte", "cancel": "abbrechen"}}


@dataclass
class Extraction:
    intent: str
    pizza: str | None
    excluded: list[str]
    option_number: int | None

    @classmethod
    def from_json(cls, raw: str) -> "Extraction":
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise LLMError(f"extraction is not JSON: {raw[:200]}") from e
        if not isinstance(data, dict):
            raise LLMError("extraction is not an object")
        pizza = data.get("pizza")
        excluded = data.get("excluded_ingredients") or []
        option = data.get("option_number")
        return cls(
            intent=str(data.get("intent") or "chat"),
            pizza=pizza.strip() if isinstance(pizza, str) and pizza.strip() else None,
            excluded=[str(x).strip() for x in excluded if isinstance(x, (str, int))] if isinstance(excluded, list) else [],
            option_number=option if isinstance(option, int) else None,
        )


class PizzaAgent:
    """Same interface as DialogEngine (greet / set_language / handle), with an LLM in front."""

    def __init__(self, engine: DialogEngine, llm: LLMClient):
        self.engine = engine
        self.llm = llm
        self.name = llm.name
        self._resolver = engine.resolver
        recipes = engine.recipes.all()
        self.menu_names = sorted(rec.name for rec in recipes)
        self.menu_lines = {
            lang: [f"{rec.name}: {', '.join(ingredient_display_name(i.name, lang) for i in rec.ingredients)}"
                   for rec in sorted(recipes, key=lambda x: x.name)]
            for lang in ("en", "de")
        }

    # --- same interface as the engine -------------------------------------------------

    def greet(self, session: Session) -> Reply:
        reply = self.engine.greet(session)
        self._remember(session, "assistant", reply.text)
        return reply

    def set_language(self, session: Session, language: str) -> Reply:
        reply = self.engine.set_language(session, language)
        session.history = []
        self._remember(session, "assistant", reply.text)
        return reply

    def handle(self, session: Session, text: str) -> Reply:
        text = (text or "").strip()
        if find_trigger(parse(text)) is not None or session.state == DialogState.CUSTOMIZING:
            # Custom pizzas are read by the rules: every topping must be an exact ingredient.
            kind, reply = self._kind(session, self.engine.handle(session, text))
            return self._phrase_and_finish(session, text, kind, reply)
        try:
            extraction = self._extract(session, text)
            log.info("extraction for %r: %s", text, extraction)
        except LLMError as e:
            log.warning("LLM extraction failed, using rules only: %s", e)
            reply = self.engine.handle(session, text)
            return self._finish(session, text, reply)

        kind, reply = self._process(session, text, extraction)
        return self._phrase_and_finish(session, text, kind, reply)

    def _phrase_and_finish(self, session: Session, text: str, kind: str, reply: Reply) -> Reply:
        try:
            phrased = self._phrase(session, text, kind, reply)
        except LLMError as e:
            log.warning("LLM reply failed, using the engine's text: %s", e)
            phrased = reply.text
        return self._finish(session, text, Reply(phrased, reply.suggestions, reply.order, reply.missing))

    # --- step 1: understanding --------------------------------------------------------

    def _extract(self, session: Session, text: str) -> Extraction:
        open_question = session.candidates if session.state == DialogState.CLARIFYING else None
        messages = [{"role": "system", "content": prompts.extraction_system(self.menu_names, open_question)}]
        # Only our last message, so "yes" or "the second one" can be understood. Older turns
        # make the model repeat earlier pizzas.
        last = next((m for m in reversed(session.history) if m["role"] == "assistant"), None)
        if last:
            messages.append(last)
        messages.append({"role": "user", "content": text})
        raw = self.llm.chat(messages, schema=prompts.EXTRACTION_SCHEMA, temperature=0, max_tokens=150)
        return Extraction.from_json(raw)

    # --- step 2 and 3: grounding, then the rule engine --------------------------------

    def _process(self, session: Session, text: str, ex: Extraction) -> tuple[str, Reply]:
        lang = session.language
        vocab = WORDS.get(lang, WORDS["en"])
        rules = parse(text)
        engine = self.engine

        if rules.says_bye and self._only_small_talk(rules):
            session.reset_pending()
            return "info", Reply(r.say(lang, "goodbye"))
        if rules.wants_cancel or ex.intent == "cancel":
            return self._kind(session, engine.handle(session, vocab["cancel"], original=text))

        clarifying = session.state == DialogState.CLARIFYING
        if clarifying:
            # Answers to "did you mean ...?": plain words are read by the rules first.
            candidates = session.candidates
            n = len(candidates)
            if rules.ordinal is not None and rules.ordinal < n:
                return self._kind(session, engine.handle(session, text))
            if rules.says_no and self._only_small_talk(rules):
                return self._kind(session, engine.handle(session, vocab["no"], original=text))
            if rules.says_yes and n == 1:
                request = self._with_exclusions(candidates[0], rules, ex, vocab["without"])
                return self._kind(session, engine.handle(session, request, original=text))
            if ex.intent == "choose_option" and ex.option_number and 1 <= ex.option_number <= n:
                return self._kind(session, engine.handle(session, str(ex.option_number), original=text))
            picked = self.engine.matcher.find_by_name(ex.pizza) if ex.pizza else None
            if picked and picked.name in candidates and ex.intent in ("order", "yes", "choose_option"):
                # The pizza was offered in our own question, so the conversation grounds it.
                request = self._with_exclusions(picked.name, rules, ex, vocab["without"])
                return self._kind(session, engine.handle(session, request, original=text))
            if ex.intent in ("yes", "no") and not ex.pizza:
                return self._kind(session, engine.handle(session, vocab[ex.intent], original=text))

        if rules.says_no and self._only_small_talk(rules) and not clarifying:
            return self._kind(session, engine.handle(session, vocab["no"], original=text))

        # Answers to our own recommendations: "yes please", "the first one", "the Funghi".
        if not clarifying:
            offered = self._offered_pizzas(session)
            chosen = None
            if rules.ordinal is not None and rules.ordinal < len(offered):
                chosen = offered[rules.ordinal]
            elif ex.intent == "choose_option" and ex.option_number and 1 <= ex.option_number <= len(offered):
                chosen = offered[ex.option_number - 1]
            elif (rules.says_yes or ex.intent == "yes") and len(offered) == 1 and self._only_small_talk(rules):
                chosen = offered[0]
            elif ex.pizza and ex.intent in ("order", "yes"):
                picked = self.engine.matcher.find_by_name(ex.pizza)
                if picked and picked.name in offered and self._grounded_pizza(ex.pizza, rules) is None:
                    chosen = picked.name   # named loosely, but we offered it ourselves
            if chosen:
                request = self._with_exclusions(chosen, rules, ex, vocab["without"])
                return self._kind(session, engine.handle(session, request, original=text))

        if ex.intent in ("order", "choose_option") and not rules.is_vague:
            request = self._order_request(rules, ex, vocab["without"])
            if request is not None:
                return self._kind(session, engine.handle(session, request, original=text))

        if ex.intent == "menu" or rules.wants_menu:
            reply = engine.handle(session, vocab["menu"], original=text)
            return "menu", reply
        if ex.intent == "no" and not clarifying:
            return self._kind(session, engine.handle(session, vocab["no"], original=text))

        # Small talk, questions, "yes" without context: the LLM answers on its own.
        if clarifying:
            fallback = r.say(lang, "clarify_again", options=r.numbered_options(lang, session.candidates))
            return "chat", Reply(fallback, list(session.candidates))
        return "chat", Reply(r.say(lang, "not_understood"), r.SUGGESTIONS[lang])

    def _order_request(self, rules: ParsedMessage, ex: Extraction, without: str) -> str | None:
        """Build "<pizza> without <a>, <b>" from grounded parts, or None when nothing was ordered."""
        pizza = self._grounded_pizza(ex.pizza, rules) if ex.pizza else None
        if pizza is None:
            # The LLM saw no believable pizza. Use the raw message if the rules find one in it,
            # or if it names something short that may be a pizza we don't have ("Lahmacun").
            content = [t for t in rules.pizza_tokens if not t.norm.isdigit()]
            if content and self.engine.matcher.match(rules.pizza_tokens).kind != MatchKind.NONE:
                return rules.text
            if ex.intent == "order" and 0 < len(content) <= 3 and not any(t.norm in ORDINALS for t in content):
                return rules.text
            return None
        return self._with_exclusions(pizza, rules, ex, without)

    def _with_exclusions(self, pizza: str, rules: ParsedMessage, ex: Extraction, without: str) -> str:
        """Exclusions the LLM found (if the customer wrote them) plus those the rules found."""
        excluded = [e for e in ex.excluded if self._grounded_words(e, rules)]
        excluded += [" ".join(t.raw for t in chunk) for chunk in rules.exclusion_chunks]
        seen, items = set(), []
        for item in excluded:
            key = " ".join(content_words(item))
            if key and key not in seen and fold(item) not in PLACEHOLDERS:
                seen.add(key)
                items.append(item)
        return f"{pizza} {without} {', '.join(items)}" if items else pizza

    def _grounded_pizza(self, pizza: str, rules: ParsedMessage) -> str | None:
        """Accept the LLM's pizza only if the customer's own words support it."""
        recipe = self.engine.matcher.find_by_name(pizza)
        if recipe is None:
            match = self.engine.matcher.match(tokenize(pizza))
            recipe = match.recipe if match.kind == MatchKind.EXACT else None
        if recipe is None:
            # Not on the menu (e.g. "Lahmacun"): keep it only if the customer wrote those words.
            return pizza if self._grounded_words(pizza, rules) else None

        match = self.engine.matcher.match(rules.pizza_tokens, restrict_to=[recipe.name])
        if match.kind == MatchKind.EXACT:
            if self.engine._unknown_neighbours(rules, match):
                return None   # "Chicken Tikka": let the rules report it as not on the menu
            return recipe.name
        # Described by its toppings ("the one with pear and gorgonzola"). Only specific
        # ingredient words count; vague ones like "spicy" or "cheese" are not enough.
        toppings = {i.name for i in recipe.ingredients} - BASE_INGREDIENTS
        terms, _ = self.engine.resolver.resolve(rules.pizza_tokens)
        mentioned = {n for t in terms if len(t.names) <= 2 for n in t.names} & toppings
        if toppings and (len(mentioned) >= 2 or mentioned == toppings):
            return recipe.name
        log.info("ignoring ungrounded pizza %r for %r", pizza, rules.text)
        return None

    def _offered_pizzas(self, session: Session) -> list[str]:
        """Menu pizzas named in our last message, in the order they were mentioned."""
        last = next((m["content"] for m in reversed(session.history) if m["role"] == "assistant"), "")
        text = f" {' '.join(content_words(last))} "
        found: dict[str, int] = {}
        taken: list[tuple[int, int]] = []
        # Full names first, then short names that are not part of a full name already found.
        for name in sorted(self.menu_names, key=lambda n: -len(content_words(n))):
            for phrase in (" ".join(content_words(name)), " ".join(content_words(short_name(name)))):
                pos = text.find(f" {phrase} ")
                if pos >= 0 and not any(a <= pos < b for a, b in taken):
                    found[name] = pos
                    taken.append((pos, pos + len(phrase) + 2))
                    break
        return sorted(found, key=found.get)

    @staticmethod
    def _only_small_talk(rules: ParsedMessage) -> bool:
        """The message has no words that could name a pizza ("thanks, bye", "yes please")."""
        return all(t.norm in SMALL_TALK for t in rules.pizza_tokens)

    @staticmethod
    def _grounded_words(phrase: str, rules: ParsedMessage) -> bool:
        """Every meaningful word of `phrase` appears (fuzzily) in the customer's message."""
        wanted = [w for w in content_words(phrase) if w not in STOPWORDS]
        typed = [t.norm for t in rules.tokens if not t.is_punct]
        return bool(wanted) and all(any(similarity(w, t) for t in typed) for w in wanted)

    @staticmethod
    def _kind(session: Session, reply: Reply) -> tuple[str, Reply]:
        if reply.order:
            return "order", reply
        if reply.missing:
            return "not_found", reply
        if session.state == DialogState.CLARIFYING:
            return "clarify", reply
        if session.state == DialogState.CUSTOMIZING:
            return "custom_ask", reply
        return "info", reply

    # --- step 4: phrasing -------------------------------------------------------------

    def _phrase(self, session: Session, text: str, kind: str, reply: Reply) -> str:
        lang = session.language
        messages = [{"role": "system", "content": prompts.reply_system(lang, self.menu_lines[lang])}]
        messages += session.history[-6:]
        messages.append({"role": "user", "content": prompts.reply_task(kind, text, reply.text, lang)})
        out = self._clean(self.llm.chat(messages, temperature=0.6, max_tokens=180))
        if self._valid(kind, out, reply, session):
            return out
        log.info("rejected LLM reply for %s: %r", kind, out)
        return reply.text

    @staticmethod
    def _clean(out: str) -> str:
        """Drop lead-ins such as "Here's the rewritten reply:" and surrounding quotes."""
        lines = [line.strip() for line in out.strip().splitlines() if line.strip()]
        if len(lines) > 1 and lines[0].endswith(":"):
            lines = lines[1:]
        return " ".join(lines).strip().strip('"“”„').strip()

    def _valid(self, kind: str, out: str, reply: Reply, session: Session) -> bool:
        if not out or len(out) > MAX_REPLY_CHARS:
            return False
        detected = detect_language(tokenize(out), out)
        if detected and detected != session.language:
            return False
        text = fold(out)

        def mentions(name: str) -> bool:
            return fold(short_name(name)) in text or fold(name) in text

        if kind == "order" and reply.order["pizza"].get("custom"):
            # Must name the custom pizza and every chosen topping.
            names = {fold(r.say(session.language, "custom_name")), "custom", "eigene"}
            if not any(n in text for n in names):
                return False
            return all(fold(ingredient_display_name(i["name"], session.language)) in text
                       or fold(i["name"]) in text for i in reply.order["ingredients"])
        if kind == "order":
            order = reply.order
            if not mentions(order["pizza"]["name"]):
                return False
            removed = set(order["removed_ingredients"])
            for name in removed:
                shown = ingredient_display_name(name, session.language)
                if fold(shown) not in text and fold(name) not in text:
                    return False
            # The reply must not claim to leave out anything the order still contains.
            claimed = parse(out).exclusion_chunks
            kept = {i["name"] for i in order["ingredients"]}
            for chunk in claimed:
                terms, _ = self._resolver.resolve(chunk)
                if any(t.names & kept and not t.names & removed for t in terms):
                    return False
            return True
        if kind != "not_found" and any(claim in text for claim in CLAIMS_ORDER):
            return False   # only real orders may sound like confirmations
        if kind == "custom_ask":
            return "?" in out
        if kind == "clarify":
            return "?" in out and all(mentions(name) for name in session.candidates)
        if kind == "not_found" and reply.missing:
            if " ".join(words(reply.missing)) not in " ".join(words(out)):
                return False
            if session.state == DialogState.CLARIFYING:   # "...but we have X, want that?"
                rest = text.replace(fold(reply.missing), " ")
                return "?" in out and all(fold(short_name(n)) in rest for n in session.candidates)
        return True

    # --- history ----------------------------------------------------------------------

    def _finish(self, session: Session, text: str, reply: Reply) -> Reply:
        self._remember(session, "user", text)
        self._remember(session, "assistant", reply.text)
        return reply

    @staticmethod
    def _remember(session: Session, role: str, content: str) -> None:
        session.history.append({"role": role, "content": content})
        del session.history[:-HISTORY_TURNS]
