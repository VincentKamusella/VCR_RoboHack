// Where the backend lives. Empty string = same origin (the backend serves this page).
// When serving the frontend separately, set e.g. "http://localhost:8000" and add that
// page's origin to PIZZABOT_CORS_ORIGINS on the backend.
window.PIZZABOT_API_BASE = window.PIZZABOT_API_BASE ?? "";
