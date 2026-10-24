// The only module that talks to the backend. Chat responses carry just the bot's reply text
// and quick-reply suggestions; matched orders stay inside the backend.

const BASE = (window.PIZZABOT_API_BASE || "").replace(/\/$/, "");

async function request(method, path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return res.json();
}

/** Starts a conversation in the given language. Returns { session_id, reply, language, suggestions }. */
export function startSession(language) {
  return request("POST", "/api/session", { language });
}

/** Sends one user message. Returns { session_id, reply, language, suggestions }. */
export function sendMessage(sessionId, message) {
  return request("POST", "/api/chat", { session_id: sessionId, message });
}

/** The menu: every pizza with its ingredients, alphabetical. Returns { language, pizzas }. */
export function getMenu(language) {
  return request("GET", `/api/menu?language=${encodeURIComponent(language)}`);
}
