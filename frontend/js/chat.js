// Chat UI: renders messages and forwards user input to the API module.
import { sendMessage, startSession } from "./api.js";

const SESSION_KEY = "pizzabot.session";

const log = document.getElementById("log");
const form = document.getElementById("form");
const input = document.getElementById("input");
const suggestionsEl = document.getElementById("suggestions");
const restartBtn = document.getElementById("restart");

let sessionId = null;
let busy = false;

function saveSession(id) {
  sessionId = id;
  try { sessionStorage.setItem(SESSION_KEY, id); } catch { /* storage unavailable */ }
}

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
  el.setAttribute("aria-label", "Bot is typing");
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
  form.querySelector("button").disabled = value;
}

async function submit(text) {
  const message = text.trim();
  if (!message || busy) return;
  addMessage(message, "user");
  input.value = "";
  renderSuggestions();
  setBusy(true);
  const typing = showTyping();
  try {
    const data = await sendMessage(sessionId, message);
    saveSession(data.session_id);
    typing.remove();
    addMessage(data.reply, "bot");
    renderSuggestions(data.suggestions);
  } catch (err) {
    typing.remove();
    addMessage("Sorry, I can't reach the kitchen right now. Please try again. / Die Küche ist gerade nicht erreichbar.", "error");
    console.error(err);
  } finally {
    setBusy(false);
    input.focus();
  }
}

// Every page load or "New chat" starts a fresh conversation.
async function start() {
  log.replaceChildren();
  renderSuggestions();
  setBusy(true);
  const typing = showTyping();
  try {
    const data = await startSession();
    saveSession(data.session_id);
    typing.remove();
    addMessage(data.reply, "bot");
    renderSuggestions(data.suggestions);
  } catch (err) {
    typing.remove();
    addMessage("The pizza server is not running. Start the backend and reload this page.", "error");
    console.error(err);
  } finally {
    setBusy(false);
    input.focus();
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  submit(input.value);
});
restartBtn.addEventListener("click", () => start());

start();
