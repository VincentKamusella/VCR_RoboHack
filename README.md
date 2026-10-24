# Pizza Chat

A chatbot that asks what pizza you want, in English or German, and matches your answer to a
recipe in the pizza-db database (by default at `~/pizza-db`). A local llama3:8b model, served by
Ollama, makes the conversation natural. A rule engine with fuzzy matching checks every decision
against the database. Without Ollama the bot runs on the rules alone.

- **Pizza found:** the full recipe is handed to the backend's order sink. The user only sees a
  confirmation.
- **Pizza found, minus some ingredients** ("Hawaii without pineapple", "Tonno ohne Zwiebeln"):
  the recipe is handed over without those ingredients.
- **Pizza not found:** the bot tells the user, pins the request to a wishlist for later addition
  to the database, and asks for a different pizza.
- **Menu book:** a small book in the corner of the page opens into a two-page menu with every
  pizza and its ingredients. Tapping a pizza orders it through the chat.
- **Custom pizza:** the first entry in the menu book starts with no toppings. A search box over
  every ingredient in the database lets the customer add exactly the toppings they want.
- **Language toggle:** English is the default. The EN/DE switch in the top bar changes the
  whole page to German and starts a new chat with a German intro.

```
You:  Ich hätte gerne eine Hawaii ohne Ananas, bitte
Bot:  Gute Wahl: Pizza Hawaii ohne Ananas. Deine Bestellung ist notiert! 🍕

You:  Pizza Lahmacun
Bot:  Sorry, we don't have “Lahmacun” on our menu. I've noted it as a wish for the future. 📝
      Which other pizza would you like?
```

## Quick start

You need Python 3.10+ and a built pizza-db database.

```sh
# 1. Build the recipe database (once, in the pizza-db project)
cd ~/pizza-db && make build

# 2. Install and run the chatbot (in this repository)
make install
make run            # serves the chat at http://localhost:8000
```

`make run` expects the database at `~/pizza-db/build/pizza.db`. Point it somewhere else with
`PIZZA_DB_PATH=/path/to/pizza.db make run`.

For the natural conversation, Ollama must be running with the model installed:

```sh
ollama pull llama3:8b      # once
ollama serve               # if it is not already running as an app
```

The chatbot picks the model up automatically at startup. `GET /api/health` shows which one is
active: `"assistant": "llama3:8b"` or `"assistant": "rules"`.

Without make:

```sh
cd backend
pip install -r requirements-dev.txt
PIZZA_DB_PATH=~/pizza-db/build/pizza.db uvicorn app.main:create_app --factory --reload
```

## Project layout

Frontend and backend are separate. The frontend only knows two HTTP endpoints. It never sees
recipe data.

```
backend/
  app/
    main.py              FastAPI app factory: wires routes, CORS and static frontend
    config.py            Settings from environment variables
    container.py         Builds and connects all services in one place
    models.py            Public API request/response schemas
    admin.py             CLI for the wishlist and orders
    agent/
      agent.py           Conversation agent: llama understands and talks, the rules decide
      llm.py             Small Ollama client (standard library only)
      prompts.py         Prompts for understanding messages and for phrasing replies
    api/
      chat.py            Public routes used by the frontend
      internal.py        Token-protected routes for other systems (robot, agent, admin)
    core/
      parser.py          Splits a message into pizza words, exclusions and intents
      matcher.py         Matches pizza words to recipe names and aliases (fuzzy)
      ingredients.py     Maps ingredient words (EN/DE) to database ingredients
      dialog.py          Conversation logic and state transitions
      custom.py          Custom pizza: recognizing the request and its toppings
      session.py         In-memory sessions
      responses.py       Everything the bot says, in English and German
      lexicon.py         Vocabulary: stopwords, exclusion words, aliases, translations
      text.py            Folding, tokenizing, fuzzy comparison
    data/
      recipes.py         Read-only access to pizza-db
      state_store.py     The bot's own SQLite file: orders and wishlist
    services/
      order_sink.py      Internal hand-off of matched recipes
      wishlist.py        Pins pizzas that are missing from the menu
      menu.py            Alphabetical menu and ingredient list for the menu book
  tests/                 pytest suite with its own small fixture database
frontend/
  index.html             Chat page
  css/chat.css           Chat styles, light and dark mode
  css/book.css           Menu book styles: corner book, open spread, page turning
  js/config.js           Backend URL (empty = same origin)
  js/api.js              The only module that calls the backend
  js/i18n.js             UI texts in English and German, current language
  js/menu-book.js        The menu book component
  js/chat.js             Chat rendering, language toggle and input handling
```

## Conversation agent

llama3:8b does two jobs: it understands the customer and it phrases the replies. The decisions
stay with the rule engine, which also feeds the wishlist and the order sink.

```
customer message
  -> llama: extract intent, pizza and excluded ingredients as JSON
  -> grounding: keep only what the customer's own words support
  -> normalized request, e.g. "Meat Lovers Pizza without bacon"
  -> rule engine: match the database, take the order or pin the wish
  -> llama: rewrite the engine's answer in a friendly tone
  -> checks: facts kept? right language? no false claims? Otherwise use the engine's text
```

**Understanding.** The model returns structured JSON with the intent, pizza, excluded
ingredients and a chosen option number. It handles free phrasing like "hold the pineapple pls",
"I'm allergic to nuts, can I get the goat cheese one?" or "die mit Käse, aber ohne Gorgonzola".

**Grounding.** A small model sometimes invents things, so its answer is checked against the
customer's words.

- A menu pizza counts only if the customer named it, or named at least two of its specific
  toppings.
- A pizza the bot itself just offered also counts, for example in reply to "Would you like
  that?" or "the first one".
- "Chicken Tikka" is not ordered as Pizza Chicken. It is pinned as a wish, and Pizza Chicken
  is offered instead.
- An excluded ingredient counts only if the customer actually wrote it. Exclusions the rules
  find are always added.
- Vague requests like "something with mushrooms" get recommendations instead of an order.
- Plain answers such as "yes", "no thanks", "the second one" and "bye" are read by the rules
  first.

**Phrasing.** The model rewrites each answer in a friendly tone in the chosen language. A
rewrite is thrown away, and the engine's own text is used, in these cases:

- A confirmation drops the pizza or a removed ingredient.
- A reply claims to leave out something the order still contains.
- A question to the customer drops its options or its question.
- A reply is in the wrong language.
- A reply that isn't an order confirmation sounds like one.

**Free conversation.** Greetings, questions and requests for recommendations get answers from
the model with the whole menu as context. The model is told to recommend only real pizzas, to
point to the menu book, and to steer towards an order.

**Fallback.** If Ollama is not running or a call fails, that message is handled by the rules
alone. The chat keeps working, just less chatty.

## Menu book and language

**Language comes first.** The page starts in English. Every text on the page, the chat intro
and the menu book follow the language chosen with the EN/DE toggle in the top bar. Switching
clears the chat and starts a new conversation that opens with an intro in the new language.

**The menu book** sits in the bottom-right corner as a small leather-bound book.

- Clicking it opens the book in the middle of the screen as a two-page spread.
- Pizzas are sorted alphabetically by their distinctive name, so "Pizza Hawaii" is filed under
  H and "BBQ Chicken Pizza" under B.
- Each page holds up to 10 pizzas with their ingredients. Ingredient names are translated
  in German.
- The left page number sits in the bottom-left corner and the right one in the bottom-right.
- "Previous" and "Next" turn the page with a page-flip animation. The arrow keys work too.
- Escape, the close button or a click outside closes the book.
- Tapping a pizza opens it in place and shows its ingredients, each with a minus button.
  Tapping the minus leaves that ingredient out, and tapping it again puts it back.
- "Order" closes the book and sends the request to the chat, for example
  "Pizza Calzone without Ricotta and Salami" or "Pizza Döner ohne Zwiebeln". "Cancel" or
  Escape closes the pizza again.
- On screens narrower than 760 pixels the book shows one page at a time.

**Custom Pizza.** The first entry on page 1 is the Custom Pizza ("Eigene Pizza" in German).

- Opening it shows no toppings, an empty "No toppings yet." note and a search box.
- The search box lists every ingredient from the database in the chosen language, with its
  category. Typing filters the list, and names that start with the typed text come first.
- Clicking a suggestion, or pressing Enter, adds it as a topping. The arrow keys move through
  the list, and Escape closes it.
- Each chosen topping has a minus to remove it again. "Order" stays disabled until at least
  one topping is chosen.
- Ordering sends e.g. "Custom Pizza with Salami, Mozzarella and Jalapeños" to the chat.

Customers can also type it: "Custom Pizza with tuna and corn", "Eigene Pizza mit Feta und
Spinat" or "I want to build my own pizza". The last one makes the bot ask for toppings, and the
next message is read as the topping list. Words that fit several ingredients, like "cheese" or
"onions", are not guessed: the bot asks for the exact one. The order for the internal hand-off
uses the name "Custom Pizza" with `"custom": true` and the chosen ingredients.
- Opening the page with `#menu` at the end of the address opens the book directly.

## How a message is processed

1. **Tokenize and fold.** Text is lowercased and accents are removed, so "Döner", "doner" and
   "DÖNER" are the same. "ß" becomes "ss".
2. **Split off exclusions.** Exclusion words start a list of unwanted ingredients. English words
   are `without`, `no`, `hold`, `minus`, `except`, `leave`, `remove` and `skip`. German words
   are `ohne`, `kein`, `keine`, `keinen` and `außer`. German postfix forms like
   "Zwiebeln weglassen" or "Zwiebeln weg" work too. A list ends at words like `on`, `but`,
   `aber` or `with`, so "No onions on my Tonno" works.
3. **Pick the reply language.** The bot answers in the language chosen with the toggle, which
   defaults to English. Messages are understood in both languages either way. API clients
   that never set a language get automatic detection from typical words.
4. **Match the pizza.**
   - Recipe names and aliases are compared word by word with fuzzy matching, so "margarita",
     "capriciosa" and "doener" work.
   - Longer names win, so "Salami e Funghi" beats "Salami".
   - Aliases cover translations and nicknames like "four cheese", "Vier Jahreszeiten",
     "Thunfisch", "hawaiian" and "kebab".
5. **Resolve exclusions** against the matched recipe's ingredients.
   - Words in both languages work, for example "Ananas", "Zwiebeln" and "olives".
   - Group words remove several ingredients. "No onions" removes white and red onion.
     "Ohne Käse" removes every cheese.
   - An ingredient's exact name removes only that ingredient. "Without Onion" keeps the
     Red Onion, which is how requests from the menu book stay precise.
6. **Decide what to do.**

| Situation | What the user sees | What happens internally |
|---|---|---|
| One pizza clearly named | Confirmation, with any removed ingredients | Order with the final ingredient list goes to the order sink |
| Several pizzas fit ("quattro") | "Did you mean 1) … or 2) …?" | Exclusions are kept until the user picks one |
| Explicit alternatives ("Salami or Margherita") | Same question | Same |
| Only part of a name fits ("goat") | "Did you mean Pizza Goat Cheese & Honey?" | If the user says no, the request is pinned to the wishlist |
| A known name plus an unknown word ("Chicken Tikka") | Not on the menu, but Pizza Chicken is offered | "Chicken Tikka" is pinned to the wishlist |
| Nothing matches ("Lahmacun") | Not on the menu, asks for another pizza | Request is pinned to the wishlist |
| Excluded ingredient isn't on the pizza | Order confirmed with a short note | Listed under `ignored.not_on_pizza` |
| Extra ingredient requested ("Margherita with ham") | Note that extras can't be added | Order without it, listed under `ignored.additions` |

Other inputs:

- **Greetings** get a greeting back.
- **"Menu", "Speisekarte" or "what do you have"** list all pizzas.
- **"Cancel" or "abbrechen"** resets an open question.
- **"No" or "nein"** after an order ends the conversation politely.

## Internal output

Matched recipes never go to the browser. Each order is passed to an **order sink**:

```json
{
  "order_id": "d0bcf61f9c434c37bfb07cfa0786cea2",
  "created_at": "2026-10-23T20:33:56+00:00",
  "session_id": "g7E70uOJFDo84FtFiW6QBg",
  "language": "en",
  "message": "Meat lovers no bacon and no beef",
  "pizza": {"id": 48, "slug": "meat-lovers-pizza", "name": "Meat Lovers Pizza", "style": "American", "origin": "USA"},
  "base": "standard pizza dough",
  "ingredients": [
    {"name": "Tomato Sauce", "category": "sauce"},
    {"name": "Mozzarella", "category": "cheese"},
    {"name": "Pepperoni", "category": "meat"},
    {"name": "Italian Sausage", "category": "meat"},
    {"name": "Cooked Ham", "category": "meat"}
  ],
  "removed_ingredients": ["Bacon", "Ground Beef"],
  "ignored": {"not_on_pizza": [], "unknown": [], "additions": []}
}
```

The default sink stores orders in `backend/var/pizzabot.db`. To send orders to a robot or an
agent instead, write a class with a `submit(order)` method and pass it to `create_app`:

```python
from app.main import create_app
from app.services.order_sink import FanOutOrderSink, StoreOrderSink

class RobotSink:
    def submit(self, order: dict) -> None:
        robot.make_pizza(order["ingredients"])   # your integration here

app = create_app(order_sink=RobotSink())
```

`FanOutOrderSink` sends each order to several sinks, for example the store and the robot.

### Reading orders and the wishlist

From the command line:

```sh
make wishlist                                   # requested pizzas that are not on the menu
make orders                                     # latest 10 orders
cd backend && python -m app.admin resolve lahmacun added   # mark a wish as done
```

Over HTTP, other systems can use the internal endpoints. They exist only when
`PIZZABOT_INTERNAL_TOKEN` is set, and each request must send the token:

```sh
curl -H "X-Internal-Token: $PIZZABOT_INTERNAL_TOKEN" localhost:8000/internal/orders
curl -H "X-Internal-Token: $PIZZABOT_INTERNAL_TOKEN" localhost:8000/internal/wishlist
```

To add a wished-for pizza to the menu, add it to `data/pizzas.json` in pizza-db, run
`make build` there, restart the chatbot, and mark the wish as `added`.

## Public API

| Method | Path | Body | Response |
|---|---|---|---|
| `POST` | `/api/session` | `{language}`, optional, `en` or `de` | `{session_id, reply, language, suggestions}` with the greeting |
| `POST` | `/api/chat` | `{session_id, message}` | `{session_id, reply, language, suggestions}` |
| `GET` | `/api/menu?language=en` | none | `{language, pizzas: [{name, short_name, ingredients}], ingredients: [{name, label, category}]}` |
| `GET` | `/api/health` | none | `{status, pizzas}` |

The menu endpoint is the printed menu: names and ingredients for the menu book. Orders matched
in the chat are never returned to the browser.

An unknown or expired `session_id` silently starts a new session. Messages are limited to
500 characters. Interactive API docs are at `http://localhost:8000/docs`.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `PIZZA_DB_PATH` | `~/pizza-db/build/pizza.db` | Recipe database, opened read-only |
| `PIZZABOT_STATE_DB` | `backend/var/pizzabot.db` | Orders and wishlist |
| `PIZZABOT_INTERNAL_TOKEN` | unset | Enables `/internal/*` routes |
| `PIZZABOT_SESSION_TTL` | `3600` | Seconds before an idle chat session expires |
| `PIZZABOT_CORS_ORIGINS` | unset | Comma-separated origins allowed to call the API |
| `PIZZABOT_LLM` | `auto` | `auto` uses Ollama when the model is available, `ollama` requires it, `off` uses only the rules |
| `PIZZABOT_OLLAMA_URL` | `http://localhost:11434` | Ollama server |
| `PIZZABOT_OLLAMA_MODEL` | `llama3:8b` | Model name as shown by `ollama list` |
| `PIZZABOT_LLM_TIMEOUT` | `60` | Seconds to wait for one model answer before using the rules |

The backend serves the frontend itself, so no CORS setup is needed by default. To host the
frontend elsewhere, set `window.PIZZABOT_API_BASE` in `frontend/js/config.js` and add the
frontend's origin to `PIZZABOT_CORS_ORIGINS`.

## Extending the vocabulary

All words live in `backend/app/core/lexicon.py`:

- `PIZZA_ALIASES` holds extra names for a pizza.
- `INGREDIENTS` holds the German display name and synonyms for each ingredient.
- `INGREDIENT_GROUPS` and `CATEGORY_WORDS` hold words that remove several ingredients.
- The exclusion, stopword and intent word lists are at the top of the file.

Umlauts can be written normally, since they are folded when the file is loaded. New pizzas from
pizza-db are matched by name automatically. Aliases are only needed for nicknames and
translations.

## Tests

```sh
make test
```

The tests build their own small recipe database, so they run without pizza-db. They cover the
parser, matching, exclusions in both languages, the wishlist, clarifications and the API,
including a check that no recipe data reaches the frontend.

The agent tests use a scripted fake model, so they run without Ollama. They check that invented
pizzas and ingredients are ignored, that wrong or off-language replies are replaced, and that
the bot falls back to the rules when the model is offline.

## Limitations

- One pizza per message. Two pizzas in one sentence can be read as one combined name, so
  "a Salami and a Funghi" becomes Pizza Salami e Funghi.
- Menu pizzas can only lose ingredients, not gain them. For other combinations there is the
  Custom Pizza.
- Sessions live in memory, so restarting the server ends open chats. Orders and the
  wishlist are stored on disk and survive restarts.
- With llama3:8b each message takes about 4 to 8 seconds on a laptop, because the model is
  called twice. The first message after startup can take longer while the model loads.
- When the bot recommends pizzas in free conversation, llama3:8b sometimes describes them
  loosely, for example calling a pizza spicy when it isn't. Orders are not affected, since the
  rules check every order against the database.
