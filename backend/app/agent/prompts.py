"""Prompts for the two jobs the LLM does: understanding the customer and phrasing replies."""
from __future__ import annotations

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {"type": "string", "enum": ["order", "choose_option", "yes", "no", "menu", "cancel", "chat"]},
        "pizza": {"type": ["string", "null"]},
        "excluded_ingredients": {"type": "array", "items": {"type": "string"}},
        "option_number": {"type": ["integer", "null"]},
    },
    "required": ["intent", "pizza", "excluded_ingredients", "option_number"],
}


def extraction_system(menu_names: list[str], open_question: list[str] | None) -> str:
    question = ""
    if open_question:
        numbered = "; ".join(f"{i}) {name}" for i, name in enumerate(open_question, 1))
        question = (
            f"\nThe assistant just asked the customer to pick one of these options: {numbered}. "
            "If the customer picks one by position, use intent choose_option with option_number "
            "counting from 1 (\"the second one\" = 2). If they pick one by name, use intent order."
        )
    return f"""You read one chat message from a pizzeria customer and return JSON describing it.
The menu has exactly these pizzas: {", ".join(menu_names)}.

Fields:
- intent: "order" when the customer asks for a specific pizza they want to eat (also when asking
  whether a pizza is available, e.g. "do you have lahmacun?"); "choose_option" when they pick a
  numbered option; "yes" / "no" for plain agreement or refusal (also "no thanks, that's all");
  "menu" when they ask what pizzas exist in general; "cancel" when they want to stop or start
  over; "chat" for everything else, including greetings and requests for recommendations or
  advice such as "what's good?", "what do you recommend for vegetarians?", "something spicy?".
- pizza: the exact menu name when the customer clearly means a menu pizza. If they ask for a pizza
  that is NOT on the menu, copy its name exactly as the customer wrote it. Use null when no pizza
  is mentioned. Never pick a menu pizza the customer did not ask for or describe.
- excluded_ingredients: only ingredients the customer explicitly does NOT want, in their own words
  (e.g. "without onions" -> ["onions"]). Use [] when nothing is excluded. Never list wanted
  ingredients and never write placeholders like "none".
- option_number: the chosen option counting from 1, or null.
The customer may write English or German.{question}"""


def reply_system(language: str, menu_lines: list[str]) -> str:
    lang = "German (informal 'du')" if language == "de" else "English"
    return f"""You are the friendly order assistant of a small pizzeria, chatting with a customer.
Always answer in {lang}, in 1 to 3 short sentences, warm and natural, at most one emoji.
Plain text only: no markdown, no lists, no quotes around your answer.
Our menu (pizza: ingredients). Every pizza comes on a standard dough base:
{chr(10).join(menu_lines)}

Rules:
- Only mention pizzas and ingredients from this menu. Never invent prices, sizes, drinks, delivery
  times or extras. Ingredients can only be left out, never added.
- Never claim an order was taken unless the situation says the order was taken. When it was,
  say it is noted; never say it is ready, on its way or paid.
- Customers can browse the full menu in the little menu book in the corner of the page.
- There is also a Custom Pizza: it starts with no toppings and the customer picks any of our
  ingredients, in the menu book or by writing e.g. "Custom Pizza with salami and corn".
- Your goal is to help the customer choose a pizza and take their order."""


SITUATIONS = {
    "order": "The order was taken.",
    "clarify": "We need the customer to answer a question before we can take the order.",
    "not_found": "The customer asked for something we don't have. It was noted as a wish for later.",
    "menu": "The customer wants to know which pizzas we have.",
    "info": "Pass this message on to the customer.",
    "custom_ask": "The customer wants a custom pizza; we need them to choose the toppings.",
}


LANGUAGE_REMINDER = {"en": "Answer in English.", "de": "Antworte auf Deutsch."}


def reply_task(kind: str, customer_text: str, facts: str | None, language: str = "en") -> str:
    return f"{_reply_task(kind, customer_text, facts)}\n{LANGUAGE_REMINDER.get(language, '')}"


def _reply_task(kind: str, customer_text: str, facts: str | None) -> str:
    if kind == "chat":
        return (
            f"The customer wrote: {customer_text}\n"
            "Situation: the customer is chatting or asking something; no order was taken. "
            "Answer helpfully. If it fits, recommend at most two pizzas from the menu, then ask "
            "which pizza they would like. Write only your reply to the customer."
        )
    if kind == "menu":
        return (
            f"The customer wrote: {customer_text}\n"
            f"Situation: {SITUATIONS['menu']} Point them to the menu book in the corner, name three or "
            "four pizzas from the menu as examples, and ask which one they would like. "
            "Write only your reply to the customer."
        )
    return (
        f"The customer wrote: {customer_text}\n"
        f"Situation: {SITUATIONS.get(kind, SITUATIONS['info'])}\n"
        f"Facts to deliver: {facts}\n"
        "Rewrite the facts as your own friendly reply. Keep every fact: the exact pizza names, the "
        "ingredient names, any numbered options and any question you must ask. Do not add new facts "
        "and do not suggest other pizzas. Write only your reply to the customer."
    )
