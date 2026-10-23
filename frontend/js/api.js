// The only module that talks to the backend. The UI never sees recipe data:
// the API returns just the bot's reply text and optional quick-reply suggestions.

const BASE = (window.PIZZABOT_API_BASE || "").replace(/\/$/, "");

async function post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return res.json();
}

/** Starts a conversation. Returns { session_id, reply, suggestions }. */
export function startSession() {
  return post("/api/session");
}

/** Sends one user message. Returns { session_id, reply, suggestions }. */
export function sendMessage(sessionId, message) {
  return post("/api/chat", { session_id: sessionId, message });
}
