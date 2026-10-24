"""The LLM agent with a scripted fake model: checks grounding, fallbacks and reply validation."""
import json

import pytest

from app.agent.agent import PizzaAgent
from app.agent.llm import LLMError
from app.core.session import Session


class FakeLLM:
    """Returns scripted extractions; replies echo the facts unless a reply is scripted."""
    name = "fake"

    def __init__(self):
        self.extractions = []
        self.replies = []
        self.fail = False

    def chat(self, messages, *, schema=None, temperature=0.3, max_tokens=300):
        if self.fail:
            raise LLMError("offline")
        if schema is not None:
            return json.dumps(self.extractions.pop(0))
        if self.replies:
            return self.replies.pop(0)
        task = messages[-1]["content"]
        if "Facts to deliver:" in task:
            return task.split("Facts to deliver:", 1)[1].split("\n")[0].strip()
        return "We have lovely pizzas. Which one would you like?"


def ex(intent="order", pizza=None, excluded=(), option=None):
    return {"intent": intent, "pizza": pizza, "excluded_ingredients": list(excluded), "option_number": option}


@pytest.fixture
def llm():
    return FakeLLM()


@pytest.fixture
def agent(engine, llm):
    return PizzaAgent(engine, llm)


@pytest.fixture
def session(agent):
    s = Session(id="t")
    agent.set_language(s, "en")
    return s


def test_llm_extraction_becomes_a_checked_order(agent, llm, session):
    llm.extractions.append(ex(pizza="Pizza Hawaii", excluded=["pineapple"]))
    reply = agent.handle(session, "hey, could I get a hawaiian but hold the pineapple pls")
    assert reply.order["pizza"]["name"] == "Pizza Hawaii"
    assert reply.order["removed_ingredients"] == ["Pineapple"]
    assert reply.order["message"].startswith("hey, could I")
    assert reply.order["interpreted_as"] == "Pizza Hawaii without pineapple"


def test_invented_pizza_is_ignored(agent, llm, session):
    llm.extractions.append(ex(pizza="Pizza Salami", excluded=["none mentioned"]))
    reply = agent.handle(session, "I'd like something nice")
    assert reply.order is None


def test_invented_exclusion_is_ignored(agent, llm, session):
    llm.extractions.append(ex(pizza="Pizza Tonno", excluded=["tuna"]))
    reply = agent.handle(session, "a tonno please")
    assert reply.order["removed_ingredients"] == []


def test_rule_exclusions_are_kept_when_llm_misses_them(agent, llm, session):
    llm.extractions.append(ex(pizza="Pizza Capricciosa"))
    reply = agent.handle(session, "Capricciosa without olives")
    assert reply.order["removed_ingredients"] == ["Black Olives"]


def test_unknown_pizza_is_pinned(agent, llm, session, store):
    llm.extractions.append(ex(pizza="Lahmacun"))
    reply = agent.handle(session, "do you have lahmacun?")
    assert reply.missing == "Lahmacun"
    assert store.missing_pizzas()[0]["requested"] == "Lahmacun"


def test_longer_unknown_name_is_not_ordered_as_the_known_part(agent, llm, session):
    llm.extractions.append(ex(pizza="Pizza Chicken"))
    reply = agent.handle(session, "Chicken Tikka please")
    assert reply.order is None
    assert reply.missing == "Chicken Tikka"
    llm.extractions.append(ex(intent="yes"))
    assert agent.handle(session, "yes, but no corn").order["removed_ingredients"] == ["Corn"]


def test_recommendation_question_does_not_order(agent, llm, session):
    llm.extractions.append(ex(intent="chat"))
    reply = agent.handle(session, "what's good if I like spicy food?")
    assert reply.order is None


def test_vague_request_gets_suggestions_and_position_picks_one(agent, llm, session):
    llm.extractions.append(ex(pizza="Pizza Funghi"))
    llm.replies.append("Try our Pizza Funghi or our Pizza Salami e Funghi. Which one?")
    reply = agent.handle(session, "something with mushrooms")
    assert reply.order is None
    llm.extractions.append(ex(intent="choose_option", option=2))
    reply = agent.handle(session, "the second one, without salami")
    assert reply.order["pizza"]["name"] == "Pizza Salami e Funghi"
    assert reply.order["removed_ingredients"] == ["Salami"]


def test_clarification_by_llm_option_number(agent, llm, session):
    llm.extractions.append(ex(pizza="Quattro"))
    agent.handle(session, "quattro")
    first = session.candidates[0]
    llm.extractions.append(ex(intent="choose_option", option=1))
    assert agent.handle(session, "the first of those").order["pizza"]["name"] == first


def test_goodbye_and_no_thanks(agent, llm, session):
    llm.extractions.append(ex(intent="cancel"))
    assert "enjoy" in agent.handle(session, "thanks, bye").text.lower()
    llm.extractions.append(ex(pizza="Pizza Diavola"))
    reply = agent.handle(session, "no thanks, that's all")
    assert reply.order is None


def test_offline_llm_falls_back_to_rules(agent, llm, session):
    llm.fail = True
    reply = agent.handle(session, "Margherita without basil")
    assert reply.order["removed_ingredients"] == ["Basil"]
    assert reply.text.startswith("Great choice")


def test_reply_missing_the_facts_is_replaced(agent, llm, session):
    llm.extractions.append(ex(pizza="Pizza Hawaii", excluded=["pineapple"]))
    llm.replies.append("Lovely, your pizza is on its way!")
    reply = agent.handle(session, "Hawaii without pineapple")
    assert reply.text.startswith("Great choice: Pizza Hawaii without Pineapple")


def test_reply_claiming_a_wrong_removal_is_replaced(agent, llm, session):
    llm.extractions.append(ex(pizza="Pizza Hawaii"))
    llm.replies.append("Great choice: Pizza Hawaii without Cooked Ham!")
    reply = agent.handle(session, "Hawaii please")
    assert reply.text.startswith("Great choice: Pizza Hawaii.")


def test_reply_in_wrong_language_is_replaced(agent, llm):
    s = Session(id="de")
    agent.set_language(s, "de")
    llm.extractions.append(ex(pizza="Pizza Salami"))
    llm.replies.append("Great choice, I have noted the Pizza Salami and the order is with the kitchen!")
    reply = agent.handle(s, "Eine Salami bitte")
    assert reply.text.startswith("Gute Wahl")


def test_chat_reply_may_not_claim_an_order(agent, llm, session):
    llm.extractions.append(ex(intent="chat"))
    llm.replies.append("I've noted your order of a Margherita!")
    reply = agent.handle(session, "tell me about your pizzas")
    assert "noted your order" not in reply.text
    assert reply.order is None


def test_custom_pizza_skips_extraction(agent, llm, session):
    # No scripted extraction: the agent must not ask the model to read this message.
    reply = agent.handle(session, "Custom Pizza with Salami and Corn")
    assert reply.order["pizza"]["name"] == "Custom Pizza"
    assert [i["name"] for i in reply.order["ingredients"]] == ["Salami", "Corn"]


def test_custom_pizza_reply_must_name_every_topping(agent, llm, session):
    llm.replies.append("Great choice: your Custom Pizza with Salami is noted!")
    reply = agent.handle(session, "Custom Pizza with Salami and Corn")
    assert reply.text.startswith("Great choice: Custom Pizza with Salami and Corn")


def test_reply_lead_in_is_removed(agent, llm, session):
    llm.extractions.append(ex(intent="chat"))
    llm.replies.append("Here's the rewritten reply:\n\n\"Hi! Which pizza would you like?\"")
    assert agent.handle(session, "hello").text == "Hi! Which pizza would you like?"
