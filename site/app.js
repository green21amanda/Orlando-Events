const CATEGORY_LABELS = {
  "food-drink": "Food & Drink",
  "arts-culture": "Arts & Culture",
  "music": "Music",
  "wellness": "Wellness",
  "market": "Market",
  "workshop-class": "Workshop / Class",
  "community": "Community",
  "family-kids": "Family & Kids",
  "other": "Other",
};

const state = {
  events: [],
  activeCategories: new Set(), // empty set = show all
  view: "calendar",
  cursor: new Date(new Date().getFullYear(), new Date().getMonth(), 1),
};

function isAllDayEvent(ev) {
  return /^\d{4}-\d{2}-\d{2}$/.test(ev.start);
}

function parseEventDate(ev) {
  // A bare "YYYY-MM-DD" is parsed by `new Date()` as UTC midnight, which
  // shifts to the previous day once converted to a US timezone for
  // display. Parse those as local midnight instead; full ISO datetimes
  // (with a time and offset) are unambiguous and pass straight through.
  if (isAllDayEvent(ev)) {
    const [year, month, day] = ev.start.split("-").map(Number);
    return new Date(year, month - 1, day);
  }
  return new Date(ev.start);
}

function formatDateHeading(date) {
  return date.toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
}

function formatEventTime(ev) {
  if (isAllDayEvent(ev)) return "Time TBD";
  const start = parseEventDate(ev);
  const startStr = start.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
  if (!ev.end) return startStr;
  const end = new Date(ev.end);
  const endStr = end.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
  return `${startStr} – ${endStr}`;
}

function dayKey(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function matchesActiveFilters(ev) {
  if (state.activeCategories.size === 0) return true;
  return ev.categories.some((c) => state.activeCategories.has(c));
}

function getFilteredEvents() {
  return state.events.filter(matchesActiveFilters);
}

// ---------- Filter bar ----------

function renderFilterBar() {
  const bar = document.getElementById("filter-bar");
  bar.innerHTML = "";

  const presentCategories = new Set();
  state.events.forEach((ev) => ev.categories.forEach((c) => presentCategories.add(c)));

  const clearChip = document.createElement("button");
  clearChip.className = "filter-chip clear-chip";
  clearChip.textContent = "All";
  clearChip.dataset.active = state.activeCategories.size === 0 ? "true" : "false";
  clearChip.addEventListener("click", () => {
    state.activeCategories.clear();
    renderFilterBar();
    renderCurrentView();
  });
  bar.appendChild(clearChip);

  Object.keys(CATEGORY_LABELS)
    .filter((cat) => presentCategories.has(cat))
    .forEach((cat) => {
      const chip = document.createElement("button");
      chip.className = "filter-chip";
      chip.dataset.active = state.activeCategories.has(cat) ? "true" : "false";
      chip.style.setProperty("--dot-color", `var(--cat-${cat})`);
      chip.innerHTML = `<span class="dot"></span>${CATEGORY_LABELS[cat]}`;
      chip.addEventListener("click", () => {
        if (state.activeCategories.has(cat)) {
          state.activeCategories.delete(cat);
        } else {
          state.activeCategories.add(cat);
        }
        renderFilterBar();
        renderCurrentView();
      });
      bar.appendChild(chip);
    });
}

// ---------- Calendar view ----------

const WEEKDAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function renderCalendar() {
  const container = document.getElementById("calendar-view");
  container.innerHTML = "";

  const monthLabel = document.getElementById("month-label");
  monthLabel.textContent = state.cursor.toLocaleDateString(undefined, {
    month: "long",
    year: "numeric",
  });

  const eventsByDay = new Map();
  getFilteredEvents().forEach((ev) => {
    const key = dayKey(parseEventDate(ev));
    if (!eventsByDay.has(key)) eventsByDay.set(key, []);
    eventsByDay.get(key).push(ev);
  });

  const grid = document.createElement("div");
  grid.className = "calendar-grid";

  WEEKDAY_LABELS.forEach((label) => {
    const cell = document.createElement("div");
    cell.className = "weekday-label";
    cell.textContent = label;
    grid.appendChild(cell);
  });

  const year = state.cursor.getFullYear();
  const month = state.cursor.getMonth();
  const firstOfMonth = new Date(year, month, 1);
  const startOffset = firstOfMonth.getDay();
  const gridStart = new Date(year, month, 1 - startOffset);

  const today = new Date();
  const todayKey = dayKey(today);

  for (let i = 0; i < 42; i++) {
    const date = new Date(gridStart.getFullYear(), gridStart.getMonth(), gridStart.getDate() + i);
    const key = dayKey(date);
    const dayEvents = (eventsByDay.get(key) || []).slice().sort((a, b) => parseEventDate(a) - parseEventDate(b));

    const cell = document.createElement("div");
    cell.className = "day-cell" + (date.getMonth() !== month ? " outside-month" : "");
    cell.dataset.today = key === todayKey ? "true" : "false";
    cell.dataset.hasEvents = dayEvents.length > 0 ? "true" : "false";

    const num = document.createElement("div");
    num.className = "day-number";
    num.textContent = date.getDate();
    cell.appendChild(num);

    const maxPills = 3;
    dayEvents.slice(0, maxPills).forEach((ev) => {
      const pill = document.createElement("div");
      pill.className = "event-pill";
      const cat = ev.categories[0] || "other";
      pill.style.setProperty("--pill-bg", `var(--cat-${cat})`);
      pill.style.setProperty("--pill-fg", "white");
      pill.textContent = ev.title;
      pill.addEventListener("click", (e) => {
        e.stopPropagation();
        openModal(ev);
      });
      cell.appendChild(pill);
    });

    if (dayEvents.length > maxPills) {
      const more = document.createElement("div");
      more.className = "more-label";
      more.textContent = `+${dayEvents.length - maxPills} more`;
      cell.appendChild(more);
    }

    if (dayEvents.length > 0) {
      cell.addEventListener("click", () => openDayAgenda(date, dayEvents));
    }

    grid.appendChild(cell);
  }

  container.appendChild(grid);
}

function openDayAgenda(date, dayEvents) {
  const body = document.createElement("div");
  const heading = document.createElement("h3");
  heading.textContent = formatDateHeading(date);
  body.appendChild(heading);
  dayEvents.forEach((ev) => body.appendChild(renderEventCard(ev)));
  showModalBody(body);
}

// ---------- Agenda (list) view ----------

function renderAgenda() {
  const container = document.getElementById("agenda-view");
  container.innerHTML = "";

  const events = getFilteredEvents()
    .slice()
    .sort((a, b) => parseEventDate(a) - parseEventDate(b));

  if (events.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "No events match the selected filters.";
    container.appendChild(empty);
    return;
  }

  let currentKey = null;
  let currentGroup = null;

  events.forEach((ev) => {
    const date = parseEventDate(ev);
    const key = dayKey(date);
    if (key !== currentKey) {
      currentKey = key;
      currentGroup = document.createElement("div");
      currentGroup.className = "agenda-group";
      const heading = document.createElement("div");
      heading.className = "agenda-date-heading";
      heading.textContent = formatDateHeading(date);
      currentGroup.appendChild(heading);
      container.appendChild(currentGroup);
    }
    currentGroup.appendChild(renderEventCard(ev));
  });
}

function renderEventCard(ev) {
  const card = document.createElement("div");
  card.className = "event-card";
  const cat = ev.categories[0] || "other";
  card.style.setProperty("--card-accent", `var(--cat-${cat})`);

  const title = document.createElement("div");
  title.className = "event-title";
  title.textContent = ev.title;
  card.appendChild(title);

  const meta = document.createElement("div");
  meta.className = "event-meta";
  meta.textContent = [formatEventTime(ev), ev.location].filter(Boolean).join(" · ");
  card.appendChild(meta);

  const cats = document.createElement("div");
  cats.className = "event-cats";
  ev.categories.forEach((c) => {
    const tag = document.createElement("span");
    tag.className = "tag";
    tag.style.setProperty("--tag-bg", `var(--cat-${c})`);
    tag.style.setProperty("--tag-fg", "white");
    tag.textContent = CATEGORY_LABELS[c] || c;
    cats.appendChild(tag);
  });
  card.appendChild(cats);

  card.addEventListener("click", () => openModal(ev));
  return card;
}

// ---------- Modal ----------

function openModal(ev) {
  const body = document.createElement("div");

  if (ev.image) {
    const img = document.createElement("img");
    img.src = ev.image;
    img.alt = "";
    body.appendChild(img);
  }

  const h3 = document.createElement("h3");
  h3.textContent = ev.title;
  body.appendChild(h3);

  const meta = document.createElement("div");
  meta.className = "modal-meta";
  const date = parseEventDate(ev);
  meta.textContent = [formatDateHeading(date), formatEventTime(ev), ev.location, ev.price]
    .filter(Boolean)
    .join(" · ");
  body.appendChild(meta);

  if (ev.description) {
    const desc = document.createElement("div");
    desc.className = "modal-desc";
    desc.textContent = ev.description;
    body.appendChild(desc);
  }

  if (ev.url) {
    const link = document.createElement("a");
    link.className = "modal-link";
    link.href = ev.url;
    link.target = "_blank";
    link.rel = "noopener";
    link.textContent = "View source →";
    body.appendChild(link);
  }

  showModalBody(body);
}

function showModalBody(bodyEl) {
  const modalBody = document.getElementById("modal-body");
  modalBody.innerHTML = "";
  modalBody.appendChild(bodyEl);
  document.getElementById("modal-backdrop").hidden = false;
}

function closeModal() {
  document.getElementById("modal-backdrop").hidden = true;
}

// ---------- View switching / rendering ----------

function renderCurrentView() {
  const count = getFilteredEvents().length;
  document.getElementById("event-count-subtitle").textContent =
    `${count} upcoming event${count === 1 ? "" : "s"}`;

  if (state.view === "calendar") {
    renderCalendar();
  } else {
    renderAgenda();
  }
}

function setView(view) {
  state.view = view;
  document.getElementById("calendar-view").hidden = view !== "calendar";
  document.getElementById("agenda-view").hidden = view !== "agenda";
  document.getElementById("month-nav").hidden = view !== "calendar";
  document.querySelectorAll(".view-toggle button").forEach((btn) => {
    btn.dataset.active = btn.dataset.view === view ? "true" : "false";
  });
  renderCurrentView();
}

// ---------- Init ----------

async function init() {
  document.querySelectorAll(".view-toggle button").forEach((btn) => {
    btn.addEventListener("click", () => setView(btn.dataset.view));
  });

  document.getElementById("prev-month").addEventListener("click", () => {
    state.cursor = new Date(state.cursor.getFullYear(), state.cursor.getMonth() - 1, 1);
    renderCurrentView();
  });
  document.getElementById("next-month").addEventListener("click", () => {
    state.cursor = new Date(state.cursor.getFullYear(), state.cursor.getMonth() + 1, 1);
    renderCurrentView();
  });
  document.getElementById("today-btn").addEventListener("click", () => {
    const now = new Date();
    state.cursor = new Date(now.getFullYear(), now.getMonth(), 1);
    renderCurrentView();
  });

  document.getElementById("modal-close").addEventListener("click", closeModal);
  document.getElementById("modal-backdrop").addEventListener("click", (e) => {
    if (e.target.id === "modal-backdrop") closeModal();
  });

  try {
    const res = await fetch("events.json", { cache: "no-store" });
    state.events = await res.json();
  } catch (err) {
    document.getElementById("event-count-subtitle").textContent =
      "Couldn't load events.json";
    console.error(err);
    return;
  }

  renderFilterBar();
  renderCurrentView();
}

init();
