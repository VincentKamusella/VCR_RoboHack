// The menu book: a small book in the corner that opens into a two-page spread.
// Up to 10 pizzas per page, alphabetical, with page turning and page numbers.
import { getMenu } from "./api.js";
import { applyI18n, getLang, t } from "./i18n.js";

const PER_PAGE = 10;
const CUSTOM_ENTRY = { name: "__custom__", custom: true };
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
 * @param {{ launcher: HTMLElement, onOrder: (message: string) => void }} options
 *   onOrder receives a chat message such as "Pizza Hawaii without Pineapple".
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

  const cache = new Map();   // language -> { pizzas, ingredients } from the API
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
        item.className = pizza.custom ? "dish-item dish-item--custom" : "dish-item";
        item.dataset.name = pizza.name;
        if (pizza.custom) item.dataset.custom = "true";
        const dish = document.createElement("button");
        dish.type = "button";
        dish.className = "dish";
        dish.setAttribute("aria-expanded", "false");
        const name = document.createElement("span");
        name.className = "dish__name";
        name.textContent = pizza.custom ? t("customName") : pizza.short_name;
        const ingredients = document.createElement("span");
        ingredients.className = "dish__ingredients";
        ingredients.textContent = pizza.custom ? t("customSubtitle") : pizza.ingredients.join(", ");
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
      pages = chunk(entries(cache.get(lang)), PER_PAGE);
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
      cache.set(lang, data);
      if (token !== loadToken) return;   // the language changed meanwhile
      pages = chunk(entries(data), PER_PAGE);
      status = "ready";
      first -= first % perSpread();
    } catch (err) {
      if (token !== loadToken) return;
      console.error(err);
      status = "error";
    }
    render();
  }

  /** The custom pizza comes first, then every menu pizza in alphabetical order. */
  function entries(data) {
    return [CUSTOM_ENTRY, ...data.pizzas];
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
    const focusable = [...book.querySelectorAll("button:not([disabled]), input")].filter((el) => !el.closest(".leaf"));
    if (!focusable.length) return;
    const firstEl = focusable[0];
    const lastEl = focusable[focusable.length - 1];
    if (e.shiftKey && document.activeElement === firstEl) { e.preventDefault(); lastEl.focus(); }
    else if (!e.shiftKey && document.activeElement === lastEl) { e.preventDefault(); firstEl.focus(); }
  }

  // --- choosing a pizza and leaving out ingredients ----------------------------

  function findPizza(name) {
    return (cache.get(getLang())?.pizzas || []).find((p) => p.name === name);
  }

  function collapseAll() {
    for (const item of spread.querySelectorAll(".dish-item.is-expanded")) {
      item.classList.remove("is-expanded");
      item.querySelector(".dish").setAttribute("aria-expanded", "false");
      item.querySelector(".dish__panel")?.remove();
    }
  }

  function setChip(chip, removed) {
    const name = chip.dataset.ingredient;
    chip.setAttribute("aria-pressed", String(removed));
    chip.setAttribute("aria-label", t(removed ? "menuRestoreIngredient" : "menuRemoveIngredient", { name }));
    chip.querySelector(".ingredient__icon").textContent = removed ? "+" : "−";
  }

  function actionButtons() {
    const actions = document.createElement("div");
    actions.className = "dish__actions";
    actions.innerHTML = `<button type="button" class="dish__cancel"></button><button type="button" class="dish__order"></button>`;
    actions.querySelector(".dish__cancel").textContent = t("menuCancel");
    actions.querySelector(".dish__order").textContent = t("menuOrder");
    return actions;
  }

  /** Opens a pizza in place: its ingredients with a minus each, plus Cancel and Order. */
  function expand(item) {
    if (item.dataset.custom) return expandCustom(item);
    const pizza = findPizza(item.dataset.name);
    if (!pizza) return;
    collapseAll();
    item.classList.add("is-expanded");
    item.querySelector(".dish").setAttribute("aria-expanded", "true");

    const panel = document.createElement("div");
    panel.className = "dish__panel";
    const hint = document.createElement("p");
    hint.className = "dish__panel-hint";
    hint.textContent = t("menuCustomiseHint");
    const chips = document.createElement("ul");
    chips.className = "dish__chips";
    for (const ingredient of pizza.ingredients) {
      const li = document.createElement("li");
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "ingredient";
      chip.dataset.ingredient = ingredient;
      chip.innerHTML = `<span class="ingredient__name"></span><span class="ingredient__icon" aria-hidden="true"></span>`;
      chip.firstChild.textContent = ingredient;
      setChip(chip, false);
      li.appendChild(chip);
      chips.appendChild(li);
    }
    panel.append(hint, chips, actionButtons());
    item.appendChild(panel);
    panel.scrollIntoView({ block: "nearest" });
    chips.querySelector(".ingredient")?.focus();
  }

  // --- custom pizza: no toppings at first, a search box adds them -------------

  let comboCount = 0;

  function expandCustom(item) {
    collapseAll();
    item.classList.add("is-expanded");
    item.querySelector(".dish").setAttribute("aria-expanded", "true");
    item.selected = [];   // [{ name, label }] in the order they were added

    const listId = `combo-list-${++comboCount}`;
    const panel = document.createElement("div");
    panel.className = "dish__panel";
    panel.innerHTML = `
      <p class="dish__panel-hint"></p>
      <ul class="dish__chips dish__selected"></ul>
      <p class="dish__empty"></p>
      <div class="combo">
        <input class="combo__input" type="search" role="combobox" autocomplete="off" spellcheck="false"
               aria-autocomplete="list" aria-expanded="false" aria-controls="${listId}">
        <ul class="combo__list" id="${listId}" role="listbox" hidden></ul>
      </div>`;
    panel.querySelector(".dish__panel-hint").textContent = t("customHint");
    panel.querySelector(".dish__empty").textContent = t("customEmpty");
    const input = panel.querySelector(".combo__input");
    input.placeholder = t("customSearch");
    input.setAttribute("aria-label", t("customSearchLabel"));
    panel.querySelector(".combo__list").setAttribute("aria-label", t("customSearchLabel"));
    panel.appendChild(actionButtons());
    item.appendChild(panel);
    renderSelected(item);
    panel.scrollIntoView({ block: "nearest" });
    input.focus();
  }

  const foldText = (s) => s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/ß/g, "ss").toLowerCase();

  function renderSelected(item) {
    const list = item.querySelector(".dish__selected");
    list.replaceChildren();
    for (const { name, label } of item.selected) {
      const li = document.createElement("li");
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "ingredient ingredient--selected";
      chip.dataset.name = name;
      chip.setAttribute("aria-label", t("customRemove", { name: label }));
      chip.innerHTML = `<span class="ingredient__name"></span><span class="ingredient__icon" aria-hidden="true">−</span>`;
      chip.firstChild.textContent = label;
      li.appendChild(chip);
      list.appendChild(li);
    }
    item.querySelector(".dish__empty").hidden = item.selected.length > 0;
    item.querySelector(".dish__order").disabled = item.selected.length === 0;
  }

  /** Shows the ingredients matching the search text (all of them for an empty search). */
  function showOptions(item) {
    const input = item.querySelector(".combo__input");
    const list = item.querySelector(".combo__list");
    const typed = input.value.trim().toLowerCase();
    const query = foldText(typed);
    const taken = new Set(item.selected.map((s) => s.name));
    // Best matches first: the name starts with the text, then a word starts with it, then any match.
    const rank = (ing) => {
      const label = foldText(ing.label);
      const words = `${label} ${foldText(ing.name)}`.split(/[\s-]+/);
      if (ing.label.toLowerCase().startsWith(typed)) return 0;   // exact spelling, umlauts included
      if (label.startsWith(query)) return 1;
      if (words.some((w) => w.startsWith(query))) return 2;
      return label.includes(query) || foldText(ing.name).includes(query) ? 3 : -1;
    };
    const matches = (cache.get(getLang())?.ingredients || [])
      .filter((ing) => !taken.has(ing.name) && (!query || rank(ing) >= 0))
      .map((ing, i) => ({ ing, i, r: query ? rank(ing) : 0 }))
      .sort((a, b) => a.r - b.r || a.i - b.i)
      .map((m) => m.ing);

    list.replaceChildren();
    item.activeOption = -1;   // nothing highlighted until the arrow keys are used
    if (!matches.length) {
      const empty = document.createElement("li");
      empty.className = "combo__none";
      empty.textContent = t("customNoMatch");
      list.appendChild(empty);
    }
    matches.forEach((ing, i) => {
      const option = document.createElement("li");
      option.className = "combo__option";
      option.id = `${list.id}-${i}`;
      option.setAttribute("role", "option");
      option.dataset.name = ing.name;
      option.dataset.label = ing.label;
      option.innerHTML = `<span class="combo__label"></span><span class="combo__category"></span>`;
      option.firstChild.textContent = ing.label;
      option.lastChild.textContent = t(`cat_${ing.category}`);
      list.appendChild(option);
    });
    list.hidden = false;
    input.setAttribute("aria-expanded", "true");
    highlightOption(item);
  }

  function highlightOption(item) {
    const options = [...item.querySelectorAll(".combo__option")];
    const input = item.querySelector(".combo__input");
    options.forEach((o, i) => o.setAttribute("aria-selected", String(i === item.activeOption)));
    const active = options[item.activeOption];
    if (active) {
      input.setAttribute("aria-activedescendant", active.id);
      active.scrollIntoView({ block: "nearest" });
    } else {
      input.removeAttribute("aria-activedescendant");
    }
  }

  function hideOptions(item) {
    const list = item?.querySelector(".combo__list");
    if (!list || list.hidden) return false;
    list.hidden = true;
    item.querySelector(".combo__input").setAttribute("aria-expanded", "false");
    item.querySelector(".combo__input").removeAttribute("aria-activedescendant");
    return true;
  }

  function addTopping(item, option) {
    item.selected.push({ name: option.dataset.name, label: option.dataset.label });
    renderSelected(item);
    const input = item.querySelector(".combo__input");
    input.value = "";
    showOptions(item);
    input.focus();
  }

  function removeTopping(item, name) {
    item.selected = item.selected.filter((s) => s.name !== name);
    renderSelected(item);
    if (!item.querySelector(".combo__list").hidden) showOptions(item);
    item.querySelector(".combo__input").focus();
  }

  function joinList(items) {
    return items.length === 1
      ? items[0]
      : `${items.slice(0, -1).join(", ")} ${t("menuAnd")} ${items[items.length - 1]}`;
  }

  /** "Pizza Hawaii without Pineapple and Cooked Ham" in the current language. */
  function orderMessage(item) {
    if (item.dataset.custom) {
      return `${t("customName")} ${t("menuWith")} ${joinList(item.selected.map((s) => s.label))}`;
    }
    const removed = [...item.querySelectorAll('.ingredient[aria-pressed="true"]')].map((c) => c.dataset.ingredient);
    if (!removed.length) return item.dataset.name;
    return `${item.dataset.name} ${t("menuWithout")} ${joinList(removed)}`;
  }

  // --- events ----------------------------------------------------------------

  launcher.addEventListener("click", open);
  closeBtn.addEventListener("click", close);
  prevBtn.addEventListener("click", () => turn("prev"));
  nextBtn.addEventListener("click", () => turn("next"));
  overlay.addEventListener("click", (e) => { if (e.target === overlay) close(); });
  spread.addEventListener("click", (e) => {
    if (animating) return;
    const item = e.target.closest(".dish-item");
    if (!e.target.closest(".combo")) hideOptions(spread.querySelector(".dish-item--custom.is-expanded"));
    if (!item) return;
    if (e.target.closest(".combo__option")) {
      addTopping(item, e.target.closest(".combo__option"));
    } else if (e.target.closest(".combo__input")) {
      showOptions(item);
    } else if (e.target.closest(".ingredient--selected")) {
      removeTopping(item, e.target.closest(".ingredient--selected").dataset.name);
    } else if (e.target.closest(".dish")) {
      if (item.classList.contains("is-expanded")) collapseAll();
      else expand(item);
    } else if (e.target.closest(".ingredient")) {
      const chip = e.target.closest(".ingredient");
      setChip(chip, chip.getAttribute("aria-pressed") !== "true");
    } else if (e.target.closest(".dish__cancel")) {
      collapseAll();
      item.querySelector(".dish").focus();
    } else if (e.target.closest(".dish__order")) {
      const message = orderMessage(item);
      close();
      onOrder(message);
    }
  });
  // Typing in the ingredient search.
  spread.addEventListener("input", (e) => {
    if (e.target.matches(".combo__input")) showOptions(e.target.closest(".dish-item"));
  });
  spread.addEventListener("keydown", (e) => {
    if (!e.target.matches(".combo__input")) return;
    const item = e.target.closest(".dish-item");
    const options = item.querySelectorAll(".combo__option");
    const open = !item.querySelector(".combo__list").hidden;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      e.stopPropagation();
      if (!open) return showOptions(item);
      const step = e.key === "ArrowDown" ? 1 : -1;
      item.activeOption = Math.max(0, Math.min(options.length - 1, item.activeOption + step));
      highlightOption(item);
    } else if (e.key === "Enter") {
      e.preventDefault();
      // Enter adds the highlighted ingredient, or the best match when none is highlighted.
      const option = options[item.activeOption] || (e.target.value.trim() ? options[0] : null);
      if (open && option) addTopping(item, option);
    } else if (e.key === "Escape" && hideOptions(item)) {
      e.stopPropagation();   // first Escape only closes the suggestions
    } else if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
      e.stopPropagation();   // move the text cursor, don't turn the page
    }
  });
  overlay.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && spread.querySelector(".dish-item.is-expanded")) {
      const item = spread.querySelector(".dish-item.is-expanded");
      collapseAll();
      item.querySelector(".dish").focus();
    } else if (e.key === "Escape") close();
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
