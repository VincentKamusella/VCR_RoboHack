// Chat UI: renders messages, the language toggle and the menu book, and forwards input to the API.
import { sendMessage, startSession } from "./api.js";
import { applyI18n, getLang, setLang, t } from "./i18n.js";
import { createMenuBook } from "./menu-book.js";

const log = document.getElementById("log");
const form = document.getElementById("form");
const input = document.getElementById("input");
const sendBtn = form.querySelector("button");
const suggestionsEl = document.getElementById("suggestions");
const restartBtn = document.getElementById("restart");
const langButtons = document.querySelectorAll(".lang-toggle__option");

let sessionId = null;
let busy = false;

function addMessage(text, who) {
  const bubble = document.createElement("div");
  bubble.className = `msg msg--${who}`;
  bubble.textContent = text;
  log.appendChild(bubble);
  log.scrollTop = log.scrollHeight;
  return bubble;
}

function showTyping() {
  const el = addMessage("", "bot");
  el.classList.add("msg--typing");
  el.setAttribute("aria-label", t("typing"));
  el.innerHTML = "<span></span><span></span><span></span>";
  return el;
}

function renderSuggestions(items = []) {
  suggestionsEl.replaceChildren();
  for (const text of items) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "chip";
    chip.textContent = text;
    chip.addEventListener("click", () => submit(text));
    suggestionsEl.appendChild(chip);
  }
}

function setBusy(value) {
  busy = value;
  sendBtn.disabled = value;
}

/** Runs one backend call with a typing indicator and shows the bot's reply. */
async function botTurn(call, errorKey) {
  setBusy(true);
  renderSuggestions();
  const typing = showTyping();
  try {
    const data = await call();
    sessionId = data.session_id;
    typing.remove();
    addMessage(data.reply, "bot");
    renderSuggestions(data.suggestions);
  } catch (err) {
    typing.remove();
    addMessage(t(errorKey), "error");
    console.error(err);
  } finally {
    setBusy(false);
    input.focus();
  }
}

function submit(text) {
  const message = text.trim();
  if (!message || busy) return;
  addMessage(message, "user");
  input.value = "";
  botTurn(() => sendMessage(sessionId, message), "errorReach");
}

/** Every page load or "New chat" starts a fresh conversation in the selected language. */
function start() {
  log.replaceChildren();
  sessionId = null;
  botTurn(() => startSession(getLang()), "errorServer");
}

function selectLanguage(lang) {
  if (lang === getLang() || busy) return;
  setLang(lang);
  applyI18n();
  for (const btn of langButtons) btn.setAttribute("aria-pressed", String(btn.dataset.lang === lang));
  book.setLanguage();
  // A language switch always starts a fresh chat, greeted in the new language.
  start();
}

// The language is fixed before anything else renders: English unless the toggle says otherwise.
setLang("en");
applyI18n();

const book = createMenuBook({
  launcher: document.getElementById("menu-launcher"),
  onOrder: (pizzaName) => submit(pizzaName),
});

form.addEventListener("submit", (e) => {
  e.preventDefault();
  submit(input.value);
});
restartBtn.addEventListener("click", () => { if (!busy) start(); });
for (const btn of langButtons) btn.addEventListener("click", () => selectLanguage(btn.dataset.lang));

start();

// A link to /#menu opens the menu book directly.
if (location.hash === "#menu") book.open();
