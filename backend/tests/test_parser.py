from app.core.parser import parse


def norms(tokens):
    return [t.norm for t in tokens]


def chunks(msg):
    return [norms(c) for c in msg.exclusion_chunks]


def test_plain_request():
    msg = parse("I'd like a Pizza Margherita please")
    assert norms(msg.pizza_tokens) == ["margherita"]
    assert msg.exclusion_chunks == []


def test_english_exclusion_list():
    msg = parse("Capricciosa without olives, artichokes and ham")
    assert norms(msg.pizza_tokens) == ["capricciosa"]
    assert chunks(msg) == [["olives"], ["artichokes"], ["ham"]]


def test_german_exclusion_and_language():
    msg = parse("Ich hätte gerne eine Hawaii ohne Ananas, bitte")
    assert norms(msg.pizza_tokens) == ["hawaii"]
    assert chunks(msg) == [["ananas"]]
    assert msg.language == "de"


def test_exclusion_before_pizza_name():
    msg = parse("No onions on my Tonno please")
    assert norms(msg.pizza_tokens) == ["tonno"]
    assert chunks(msg) == [["onions"]]


def test_german_postfix_exclusion():
    msg = parse("Tonno, aber die Zwiebeln bitte weglassen")
    assert norms(msg.pizza_tokens) == ["tonno"]
    assert chunks(msg) == [["zwiebeln"]]


def test_no_followed_by_comma_is_an_answer_not_an_exclusion():
    msg = parse("No, a Funghi please")
    assert norms(msg.pizza_tokens) == ["funghi"]
    assert msg.exclusion_chunks == []


def test_umlauts_are_folded():
    assert norms(parse("Döner").pizza_tokens) == ["doner"]
    assert norms(parse("Käse").pizza_tokens) == ["kase"]
