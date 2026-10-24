# Pizza Chat

A chatbot that asks what pizza you want, in English or German, and matches your answer to a
recipe in the pizza-db database (by default at `~/pizza-db`). No AI agent is involved. The bot uses
rule-based parsing and fuzzy matching.

- **Pizza found:** the full recipe is handed to the backend's order sink. The user only sees a
  confirmation.
- **Pizza found, minus some ingredients** ("Hawaii without pineapple", "Tonno ohne Zwiebeln"):
  the recipe is handed over without those ingredients.
- **Pizza not found:** the bot tells the user, pins the request to a wishlist for later addition
  to the database, and asks for a different pizza.
- **Menu book:** a small book in the corner of the page opens into a two-page menu with every
  pizza and its ingredients. Tapping a pizza orders it through the chat.
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
    api/
      chat.py            Public routes used by the frontend
      internal.py        Token-protected routes for other systems (robot, agent, admin)
    core/
      parser.py          Splits a message into pizza words, exclusions and intents
      matcher.py         Matches pizza words to recipe names and aliases (fuzzy)
      ingredients.py     Maps ingredient words (EN/DE) to database ingredients
      dialog.py          Conversation logic and state transitions
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
      menu.py            Alphabetical menu with translated ingredients for the menu book
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
- Tapping a pizza closes the book and orders it in the chat.
- On screens narrower than 760 pixels the book shows one page at a time.
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
| `GET` | `/api/menu?language=en` | none | `{language, pizzas: [{name, short_name, ingredients}]}` |
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

## Limitations

- One pizza per message. Two pizzas in one sentence can be read as one combined name, so
  "a Salami and a Funghi" becomes Pizza Salami e Funghi.
- Ingredients can only be removed, not added or swapped.
- Sessions live in memory, so restarting the server ends open chats. Orders and the
  wishlist are stored on disk and survive restarts.
