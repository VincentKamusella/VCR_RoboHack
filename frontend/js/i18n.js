// UI language. English is the default; the top-bar toggle switches it before anything else loads.

const STRINGS = {
  en: {
    newChat: "New chat",
    newChatTitle: "Start a new chat",
    placeholder: "e.g. Hawaii without pineapple",
    send: "Send",
    messageLabel: "Your message",
    languageLabel: "Language",
    typing: "Bot is typing",
    errorReach: "Sorry, I can't reach the kitchen right now. Please try again.",
    errorServer: "The pizza server is not running. Start the backend and reload this page.",
    menuOpen: "Open the menu",
    menuSpine: "Menu",
    menuTitle: "Menu",
    menuSubtitle: "All pizzas on a classic dough base",
    menuPrev: "Previous",
    menuNext: "Next",
    menuClose: "Close the menu",
    menuHint: "Tap a pizza to order it",
    menuError: "The menu could not be loaded.",
    menuLoading: "Loading…",
    menuEnd: "Buon appetito!",
    pageLabel: "Page",
  },
  de: {
    newChat: "Neuer Chat",
    newChatTitle: "Einen neuen Chat starten",
    placeholder: "z. B. Salami ohne Zwiebeln",
    send: "Senden",
    messageLabel: "Deine Nachricht",
    languageLabel: "Sprache",
    typing: "Der Bot schreibt",
    errorReach: "Die Küche ist gerade nicht erreichbar. Bitte versuch es noch einmal.",
    errorServer: "Der Pizza-Server läuft nicht. Starte das Backend und lade die Seite neu.",
    menuOpen: "Speisekarte öffnen",
    menuSpine: "Karte",
    menuTitle: "Speisekarte",
    menuSubtitle: "Alle Pizzen auf klassischem Teigboden",
    menuPrev: "Zurück",
    menuNext: "Weiter",
    menuClose: "Speisekarte schließen",
    menuHint: "Tippe auf eine Pizza, um sie zu bestellen",
    menuError: "Die Speisekarte konnte nicht geladen werden.",
    menuLoading: "Lädt…",
    menuEnd: "Buon appetito!",
    pageLabel: "Seite",
  },
};

export const LANGUAGES = ["en", "de"];
let current = "en";

export function getLang() {
  return current;
}

export function setLang(lang) {
  if (LANGUAGES.includes(lang)) current = lang;
}

export function t(key) {
  return STRINGS[current][key] ?? STRINGS.en[key] ?? key;
}

/** Fills every element marked with data-i18n, data-i18n-placeholder, -title or -aria-label. */
export function applyI18n(root = document) {
  document.documentElement.lang = current;
  for (const el of root.querySelectorAll("[data-i18n]")) el.textContent = t(el.dataset.i18n);
  for (const el of root.querySelectorAll("[data-i18n-placeholder]")) el.placeholder = t(el.dataset.i18nPlaceholder);
  for (const el of root.querySelectorAll("[data-i18n-title]")) el.title = t(el.dataset.i18nTitle);
  for (const el of root.querySelectorAll("[data-i18n-aria-label]")) el.setAttribute("aria-label", t(el.dataset.i18nAriaLabel));
}
