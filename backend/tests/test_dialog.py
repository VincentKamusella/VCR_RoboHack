from app.core.session import DialogState


def ingredient_names(order):
    return [i["name"] for i in order["ingredients"]]


def test_existing_pizza_is_returned_internally(chat, sink):
    reply = chat("Can I have a Pizza Salami?")
    assert reply.order["pizza"]["name"] == "Pizza Salami"
    assert ingredient_names(reply.order) == ["Tomato Sauce", "Mozzarella", "Salami"]
    assert sink.orders == [reply.order]
    # The recipe itself is not part of what the user reads.
    assert "Tomato Sauce" not in reply.text


def test_typos_and_aliases(chat):
    assert chat("margarita").order["pizza"]["name"] == "Pizza Margherita"
    assert chat("capriciosa").order["pizza"]["name"] == "Pizza Capricciosa"
    assert chat("four cheese").order["pizza"]["name"] == "Pizza Quattro Formaggi"
    assert chat("Vier Jahreszeiten").order["pizza"]["name"] == "Pizza Quattro Stagioni"
    assert chat("Döner").order["pizza"]["name"] == "Pizza Döner"
    assert chat("doener").order["pizza"]["name"] == "Pizza Döner"


def test_longest_name_wins(chat):
    assert chat("Salami e Funghi").order["pizza"]["name"] == "Pizza Salami e Funghi"
    assert chat("salami with mushrooms").order["pizza"]["name"] == "Pizza Salami e Funghi"
    assert chat("BBQ chicken").order["pizza"]["name"] == "BBQ Chicken Pizza"


def test_without_ingredients_english(chat):
    order = chat("Capricciosa without olives and artichokes").order
    assert order["removed_ingredients"] == ["Black Olives", "Artichokes"]
    assert ingredient_names(order) == ["Tomato Sauce", "Mozzarella", "Cooked Ham", "Mushrooms"]


def test_without_ingredients_german(chat):
    reply = chat("Ich hätte gerne eine Hawaii ohne Ananas und ohne Schinken")
    assert reply.order["removed_ingredients"] == ["Pineapple", "Cooked Ham"]
    assert ingredient_names(reply.order) == ["Tomato Sauce", "Mozzarella"]
    assert reply.text.startswith("Gute Wahl")


def test_group_words_remove_all_matching_ingredients(chat):
    assert chat("Calzone ohne Käse").order["removed_ingredients"] == ["Mozzarella", "Ricotta"]
    assert chat("Tonno no onions").order["removed_ingredients"] == ["Red Onion"]
    assert chat("Diavola, nicht so scharf bitte, ohne Chili").order["removed_ingredients"] == ["Chili Peppers"]


def test_excluding_something_not_on_the_pizza(chat):
    reply = chat("Salami without pineapple")
    assert reply.order["removed_ingredients"] == []
    assert reply.order["ignored"]["not_on_pizza"] == ["pineapple"]
    assert "doesn't come with pineapple" in reply.text


def test_unknown_exclusion_word(chat):
    reply = chat("Margherita without blorbs")
    assert reply.order["ignored"]["unknown"] == ["blorbs"]


def test_additions_are_not_added(chat):
    reply = chat("Margherita with ham")
    assert reply.order["pizza"]["name"] == "Pizza Margherita"
    assert reply.order["ignored"]["additions"] == ["ham"]
    assert "Cooked Ham" not in ingredient_names(reply.order)


def test_missing_pizza_is_pinned_and_user_asked_again(chat, store, sink):
    reply = chat("I want a Pizza Lahmacun")
    assert reply.order is None
    assert reply.missing == "Lahmacun"
    assert "Which other pizza" in reply.text
    wishes = store.missing_pizzas()
    assert [(w["requested"], w["request_count"]) for w in wishes] == [("Lahmacun", 1)]
    chat("lahmacun")
    assert store.missing_pizzas()[0]["request_count"] == 2
    assert sink.orders == []


def test_longer_unknown_name_is_pinned_with_suggestion(chat, store):
    reply = chat("Chicken Tikka")
    assert reply.missing == "Chicken Tikka"
    assert "Pizza Chicken" in reply.text
    assert store.missing_pizzas()[0]["requested"] == "Chicken Tikka"
    assert chat("yes").order["pizza"]["name"] == "Pizza Chicken"


def test_ambiguous_request_asks_and_keeps_exclusions(chat):
    reply = chat("Quattro without olives")
    assert reply.order is None
    assert chat.session.state == DialogState.CLARIFYING
    assert set(reply.suggestions) == {"Pizza Quattro Stagioni", "Pizza Quattro Formaggi"}
    order = chat("Stagioni").order
    assert order["pizza"]["name"] == "Pizza Quattro Stagioni"
    assert order["removed_ingredients"] == ["Black Olives"]


def test_clarification_by_number(chat):
    reply = chat("quattro")
    first = reply.suggestions[0]
    assert chat("1").order["pizza"]["name"] == first


def test_explicit_alternatives_are_ambiguous(chat):
    reply = chat("Salami or Margherita?")
    assert reply.order is None
    assert set(reply.suggestions) == {"Pizza Salami", "Pizza Margherita"}


def test_declined_partial_match_is_pinned(chat, store):
    reply = chat("pineapple")
    assert "Pizza Hawaii" in reply.text
    reply = chat("no")
    assert reply.missing == "pineapple"
    assert store.missing_pizzas()[0]["requested"] == "pineapple"


def test_changing_mind_during_clarification(chat):
    chat("quattro")
    assert chat("actually a Funghi").order["pizza"]["name"] == "Pizza Funghi"


def test_greeting_menu_and_cancel(chat):
    assert "pizza" in chat("Hello").text.lower()
    assert "Pizza Tonno" in chat("What do you have?").text
    chat("quattro")
    assert "instead" in chat("cancel").text
    assert chat.session.state == DialogState.AWAITING_CHOICE


def test_language_follows_user(chat):
    assert chat("Margherita bitte").text.startswith("Gute Wahl")
    assert chat("Salami please").text.startswith("Great choice")


def test_german_display_names_for_removed_ingredients(chat):
    assert "ohne Ananas" in chat("Hawaii ohne Ananas").text


def test_exact_ingredient_name_removes_only_that_ingredient(engine):
    from app.data.recipes import Ingredient, Recipe
    from app.core.session import Session
    both = Recipe(99, "both", "Pizza Both Onions", "Test", "Test",
                  (Ingredient("Onion", "vegetable"), Ingredient("Red Onion", "vegetable")))
    session = Session(id="x")
    order = engine._finalize(session, both, [_tokens("Onion")], [], "test").order
    assert order["removed_ingredients"] == ["Onion"]
    order = engine._finalize(session, both, [_tokens("onions")], [], "test").order
    assert order["removed_ingredients"] == ["Onion", "Red Onion"]


def _tokens(text):
    from app.core.text import tokenize
    return tokenize(text)


def test_menu_book_requests_remove_exactly_the_chosen_ingredients(engine):
    """The menu book sends e.g. 'Pizza Hawaii without Pineapple and Cooked Ham'. Every
    ingredient of every pizza must come back out exactly, in both languages."""
    from app.core.session import Session
    from app.services.menu import build_menu
    phrasing = {"en": ("without", "and"), "de": ("ohne", "und")}
    for lang, (without, conj) in phrasing.items():
        menu = {p["name"]: p["ingredients"] for p in build_menu(engine.recipes, lang)}
        for recipe in engine.recipes.all():
            db_names = [i.name for i in recipe.ingredients]
            shown = menu[recipe.name]
            picks = [[k] for k in range(len(db_names))] + [list(range(1, len(db_names)))]
            for pick in picks:
                parts = [shown[k] for k in pick]
                listed = parts[0] if len(parts) == 1 else f"{', '.join(parts[:-1])} {conj} {parts[-1]}"
                session = Session(id="x", language=lang, language_locked=True)
                order = engine.handle(session, f"{recipe.name} {without} {listed}").order
                assert order is not None, (lang, recipe.name, listed)
                assert order["pizza"]["name"] == recipe.name
                assert sorted(order["removed_ingredients"]) == sorted(db_names[k] for k in pick), (lang, listed)
