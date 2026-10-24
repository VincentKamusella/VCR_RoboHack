// The menu book: a small book in the corner that opens into a two-page spread.
// Up to 10 pizzas per page, alphabetical, with page turning and page numbers.
import { getMenu } from "./api.js";
import { applyI18n, getLang, t } from "./i18n.js";

const PER_PAGE = 10;
const FLIP_MS = 700;
const CLOSE_MS = 250;
const narrowScreen = window.matchMedia("(max-width: 760px)");
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

const TEMPLATE = `
  <div class="book" role="dialog" aria-modal="true">
    <button class="book__close" type="button" data-i18n-aria-label="menuClose" data-i18n-title="menuClose">
      <span aria-hidden="true">×</span>
    </button>
    <div class="book__cover">
      <div class="book__spread"></div>
    </div>
    <nav class="book__nav">
      <button class="book__turn" type="button" data-dir="prev">
        <span aria-hidden="true">‹</span> <span data-i18n="menuPrev"></span>
      </button>
      <span class="book__hint" data-i18n="menuHint"></span>
      <button class="book__turn" type="button" data-dir="next">
        <span data-i18n="menuNext"></span> <span aria-hidden="true">›</span>
      </button>
    </nav>
  </div>`;

function chunk(items, size) {
  const out = [];
  for (let i = 0; i < items.length; i += size) out.push(items.slice(i, i + size));
  return out;
}

/**
 * @param {{ launcher: HTMLElement, onOrder: (pizzaName: string) => void }} options
 */
export function createMenuBook({ launcher, onOrder }) {
  const overlay = document.createElement("div");
  overlay.className = "book-overlay";
  overlay.hidden = true;
  overlay.innerHTML = TEMPLATE;
  document.body.appendChild(overlay);

  const book = overlay.querySelector(".book");
  const spread = overlay.querySelector(".book__spread");
  const closeBtn = overlay.querySelector(".book__close");
  const prevBtn = overlay.querySelector('[data-dir="prev"]');
  const nextBtn = overlay.querySelector('[data-dir="next"]');

  const cache = new Map();   // language -> pizzas
  let pages = [];            // arrays of up to PER_PAGE pizzas
  let first = 0;             // index of the first visible page
  let status = "idle";       // idle | loading | ready | error
  let isOpen = false;
  let animating = false;
  let loadToken = 0;

  const perSpread = () => (narrowScreen.matches ? 1 : 2);
  // Page count, padded so the last spread has a closing page on the right.
  const pageCount = () => Math.max(1, pages.length + (perSpread() === 2 && pages.length % 2 ? 1 : 0));

  // --- rendering -------------------------------------------------------------

  function renderPage(index) {
    // Pages 1, 3, 5 … are left pages, 2, 4, 6 … are right pages, as in a real book.
    const side = index % 2 === 0 ? "left" : "right";
    const page = document.createElement("section");
    page.className = `page page--${side}`;
    page.setAttribute("aria-label", `${t("pageLabel")} ${index + 1}`);

    const body = document.createElement("div");
    body.className = "page__body";

    if (index === 0) {
      const head = document.createElement("header");
      head.className = "page__head";
      head.innerHTML = `<h2 class="page__title"></h2><p class="page__subtitle"></p>`;
      head.querySelector(".page__title").textContent = t("menuTitle");
      head.querySelector(".page__subtitle").textContent = t("menuSubtitle");
      body.appendChild(head);
    }

    if (status === "loading" || status === "error") {
      if (index !== first) return finishPage(page, body, index);
      const note = document.createElement("p");
      note.className = "page__note";
      note.textContent = status === "loading" ? t("menuLoading") : t("menuError");
      body.appendChild(note);
    } else if (index < pages.length) {
      const list = document.createElement("ol");
      list.className = "page__list";
      for (const pizza of pages[index]) {
        const item = document.createElement("li");
        const dish = document.createElement("button");
        dish.type = "button";
        dish.className = "dish";
        dish.dataset.name = pizza.name;
        const name = document.createElement("span");
        name.className = "dish__name";
        name.textContent = pizza.short_name;
        const ingredients = document.createElement("span");
        ingredients.className = "dish__ingredients";
        ingredients.textContent = pizza.ingredients.join(", ");
        dish.append(name, ingredients);
        item.appendChild(dish);
        list.appendChild(item);
      }
      body.appendChild(list);
    } else {
      const end = document.createElement("p");
      end.className = "page__end";
      end.innerHTML = `<span aria-hidden="true">🍕</span><span></span>`;
      end.lastChild.textContent = t("menuEnd");
      body.appendChild(end);
    }

    return finishPage(page, body, index);
  }

  function finishPage(page, body, index) {
    const number = document.createElement("div");
    number.className = "page__number";
    number.textContent = String(index + 1);
    page.append(body, number);
    return page;
  }

  function visibleIndexes() {
    return Array.from({ length: perSpread() }, (_, i) => first + i);
  }

  function render() {
    spread.classList.toggle("book__spread--single", perSpread() === 1);
    spread.replaceChildren(...visibleIndexes().map(renderPage));
    updateNav();
  }

  function updateNav() {
    const ready = status === "ready";
    prevBtn.disabled = !ready || animating || first <= 0;
    nextBtn.disabled = !ready || animating || first + perSpread() >= pageCount();
    book.setAttribute("aria-label", t("menuTitle"));
  }

  // --- page turning ----------------------------------------------------------

  function turn(direction) {
    if (status !== "ready" || animating) return;
    const step = perSpread();
    const target = direction === "next" ? first + step : first - step;
    if (target < 0 || target >= pageCount()) return;

    if (step === 1 || reducedMotion.matches) {
      first = target;
      render();
      spread.classList.remove("is-fading");
      void spread.offsetWidth;   // restart the fade animation
      spread.classList.add("is-fading");
      return;
    }
    flip(direction, target);
  }

  // A two-sided leaf turns over the spine: front = page being turned, back = page revealed.
  function flip(direction, target) {
    animating = true;
    updateNav();
    const [leftSlot, rightSlot] = spread.children;
    const leaf = document.createElement("div");
    leaf.className = `leaf leaf--${direction}`;
    const front = document.createElement("div");
    front.className = "leaf__face leaf__face--front";
    const back = document.createElement("div");
    back.className = "leaf__face leaf__face--back";

    if (direction === "next") {
      front.appendChild(rightSlot.cloneNode(true));
      back.appendChild(renderPage(target));
      spread.replaceChild(renderPage(target + 1), rightSlot);
    } else {
      front.appendChild(leftSlot.cloneNode(true));
      back.appendChild(renderPage(target + 1));
      spread.replaceChild(renderPage(target), leftSlot);
    }
    leaf.append(front, back);
    spread.appendChild(leaf);

    requestAnimationFrame(() => requestAnimationFrame(() => leaf.classList.add("is-turned")));
    setTimeout(() => {
      first = target;
      render();   // final state: both pages of the new spread
      animating = false;
      updateNav();
    }, FLIP_MS);
  }

  // --- data ------------------------------------------------------------------

  async function load() {
    const lang = getLang();
    const token = ++loadToken;
    if (cache.has(lang)) {
      pages = chunk(cache.get(lang), PER_PAGE);
      status = "ready";
      first = Math.min(first, Math.max(0, pageCount() - 1));
      first -= first % perSpread();
      render();
      return;
    }
    status = "loading";
    render();
    try {
      const data = await getMenu(lang);
      cache.set(lang, data.pizzas);
      if (token !== loadToken) return;   // the language changed meanwhile
      pages = chunk(data.pizzas, PER_PAGE);
      status = "ready";
      first -= first % perSpread();
    } catch (err) {
      if (token !== loadToken) return;
      console.error(err);
      status = "error";
    }
    render();
  }

  // --- open / close ----------------------------------------------------------

  function open() {
    if (isOpen) return;
    isOpen = true;
    overlay.hidden = false;
    document.body.classList.add("book-is-open");
    launcher.setAttribute("aria-expanded", "true");
    requestAnimationFrame(() => overlay.classList.add("is-open"));
    load();
    closeBtn.focus();
  }

  function close() {
    if (!isOpen) return;
    isOpen = false;
    overlay.classList.remove("is-open");
    document.body.classList.remove("book-is-open");
    launcher.setAttribute("aria-expanded", "false");
    setTimeout(() => { if (!isOpen) overlay.hidden = true; }, CLOSE_MS);
    launcher.focus();
  }

  function trapFocus(e) {
    const focusable = [...book.querySelectorAll("button:not([disabled])")].filter((el) => !el.closest(".leaf"));
    if (!focusable.length) return;
    const firstEl = focusable[0];
    const lastEl = focusable[focusable.length - 1];
    if (e.shiftKey && document.activeElement === firstEl) { e.preventDefault(); lastEl.focus(); }
    else if (!e.shiftKey && document.activeElement === lastEl) { e.preventDefault(); firstEl.focus(); }
  }

  // --- events ----------------------------------------------------------------

  launcher.addEventListener("click", open);
  closeBtn.addEventListener("click", close);
  prevBtn.addEventListener("click", () => turn("prev"));
  nextBtn.addEventListener("click", () => turn("next"));
  overlay.addEventListener("click", (e) => { if (e.target === overlay) close(); });
  spread.addEventListener("click", (e) => {
    const dish = e.target.closest(".dish");
    if (!dish || animating) return;
    close();
    onOrder(dish.dataset.name);
  });
  overlay.addEventListener("keydown", (e) => {
    if (e.key === "Escape") close();
    else if (e.key === "ArrowRight") turn("next");
    else if (e.key === "ArrowLeft") turn("prev");
    else if (e.key === "Tab") trapFocus(e);
  });
  narrowScreen.addEventListener("change", () => {
    first -= first % perSpread();
    if (isOpen) render();
  });

  applyI18n(overlay);

  return {
    open,
    close,
    /** Call after the UI language changed: relabels the book and reloads the menu. */
    setLanguage() {
      applyI18n(overlay);
      if (isOpen) load();
      else status = "idle";
    },
  };
}
