// Playground for the boi generator. The readings are precomputed by
// scripts/build_web_data.py, so this file only looks them up, works out the
// tone of each syllable, and keeps the URL in step with what is on screen.

const TONE_MARKS = {
  "̀": "huyền",
  "́": "sắc",
  "̃": "ngã",
  "̉": "hỏi",
  "̣": "nặng",
};
const MAX_SUGGESTIONS = 8;

const el = {
  form: document.querySelector("#search"),
  input: document.querySelector("#word"),
  submit: document.querySelector("#submit"),
  clear: document.querySelector("#clear"),
  list: document.querySelector("#suggestions"),
  result: document.querySelector("#result"),
  examples: document.querySelector("#examples"),
  status: document.querySelector("#status"),
  theme: document.querySelector("#theme"),
  count: document.querySelector("#count"),
};

const shards = new Map();
let gold = {};
let index = { examples: [], words: 0, gold: 0, agree: 0 };
let active = -1;
let suggestions = [];

/** Tone of one Vietnamese syllable, from its combining mark. */
function toneOf(syllable) {
  for (const ch of syllable.normalize("NFD")) {
    if (TONE_MARKS[ch]) return TONE_MARKS[ch];
  }
  return "ngang";
}

async function shardFor(letter) {
  if (!shards.has(letter)) {
    shards.set(letter, fetch(`./data/${letter}.json`)
      .then((r) => (r.ok ? r.json() : {}))
      .catch(() => ({})));
  }
  return shards.get(letter);
}

function icon(name) {
  const paths = {
    arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    chevron: '<path d="m9 6 6 6-6 6"/>',
  };
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"
    stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name]}</svg>`;
}

const escapeHtml = (s) =>
  s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/* Rendering ------------------------------------------------------------ */

function renderEmpty() {
  el.result.hidden = true;
  el.examples.hidden = false;
  el.status.textContent = "";
}

function renderMissing(word) {
  el.examples.hidden = true;
  el.result.hidden = false;
  el.result.removeAttribute("data-fresh");
  el.result.innerHTML = `<p class="state">No pronunciation for <b>${escapeHtml(word)}</b>.
    The generator reads phones from CMUdict, which does not list it. Try another
    spelling, or a word that is not a name.</p>`;
  el.status.textContent = `${word}: no pronunciation available`;
}

function renderLoading() {
  el.examples.hidden = true;
  el.result.hidden = false;
  el.result.removeAttribute("data-fresh");
  el.result.innerHTML = '<div class="skeleton"></div>';
}

function renderResult(word, phones, readings) {
  const [best, ...alts] = readings;
  const syllables = best.split(" ");
  const g = gold[word];

  let note = "";
  if (g) {
    const matches = [g.vi, ...g.alt].includes(best);
    note = matches
      ? `<p class="note note--agree"><span class="note-label">Matches the reviewed reading</span></p>`
      : `<p class="note note--differ"><span class="note-label">Reviewed reading</span>
           <b>${escapeHtml(g.vi)}</b></p>`;
  }

  const rows = [
    ["Phones", `<span class="phones">${escapeHtml(phones)}</span>`],
    alts.length
      ? ["Also", `<span class="alts">${alts
          .map((a) => `<button type="button" data-swap="${escapeHtml(a)}">${escapeHtml(a)}</button>`)
          .join("")}</span>`]
      : null,
    g && g.native ? ["Vietnamese word", escapeHtml(g.native)] : null,
    g && g.tags.length ? ["Tags", `<span class="tags">${escapeHtml(g.tags.join(" "))}</span>`] : null,
    g ? ["Reviewed in", `${escapeHtml(g.split)} split, ${escapeHtml(g.status)}`] : null,
  ].filter(Boolean);

  el.examples.hidden = true;
  el.result.hidden = false;
  el.result.innerHTML = `
    <p class="reading" lang="vi">${escapeHtml(best)}</p>
    <ul class="syllables">
      ${syllables.map((s, i) => `<li class="syllable" style="--i:${i}">
        <b lang="vi">${escapeHtml(s)}</b><span>${toneOf(s)}</span></li>`).join("")}
    </ul>
    ${note}
    <details class="source">
      <summary>${icon("chevron")}How it got there</summary>
      <dl>${rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("")}</dl>
    </details>`;

  // Restart the one authored moment.
  el.result.removeAttribute("data-fresh");
  void el.result.offsetWidth;
  el.result.setAttribute("data-fresh", "");

  el.status.textContent = `${word} reads as ${best}, ${syllables.length} syllable${
    syllables.length === 1 ? "" : "s"}`;
}

/* Lookup --------------------------------------------------------------- */

async function show(word, { push = true } = {}) {
  const w = word.trim().toLowerCase();
  closeSuggestions();
  if (!w) {
    renderEmpty();
    if (push) setUrl("");
    return;
  }
  if (el.input.value !== word) el.input.value = word;
  el.clear.hidden = false;
  el.submit.disabled = false;

  const pending = shardFor(w[0]);
  const timer = setTimeout(renderLoading, 120);
  const shard = await pending;
  clearTimeout(timer);

  const entry = shard[w];
  if (!entry) renderMissing(w);
  else {
    const [phones, readings] = entry.split("|");
    renderResult(w, phones, readings.split(";"));
  }
  if (push) setUrl(w);
}

function setUrl(word) {
  const url = word ? `?w=${encodeURIComponent(word)}` : location.pathname;
  if (location.search !== (word ? `?w=${encodeURIComponent(word)}` : "")) {
    history.pushState({ word }, "", url);
  }
}

/* Suggestions ---------------------------------------------------------- */

async function updateSuggestions() {
  const q = el.input.value.trim().toLowerCase();
  el.clear.hidden = !q;
  el.submit.disabled = !q;
  if (q.length < 2) return closeSuggestions();

  const shard = await shardFor(q[0]);
  if (el.input.value.trim().toLowerCase() !== q) return;

  suggestions = [];
  for (const word in shard) {
    if (word.startsWith(q) && word !== q) {
      suggestions.push(word);
      if (suggestions.length >= MAX_SUGGESTIONS) break;
    }
  }
  if (!suggestions.length) return closeSuggestions();

  el.list.innerHTML = suggestions.map((w, i) => {
    const reading = shard[w].split("|")[1].split(";")[0];
    return `<li role="option" id="opt-${i}" aria-selected="false">
      <span class="s-word">${escapeHtml(w)}</span>
      <span class="s-read" lang="vi">${escapeHtml(reading)}</span></li>`;
  }).join("");
  el.list.hidden = false;
  el.input.setAttribute("aria-expanded", "true");
  setActive(-1);
}

function closeSuggestions() {
  el.list.hidden = true;
  el.list.innerHTML = "";
  el.input.setAttribute("aria-expanded", "false");
  el.input.removeAttribute("aria-activedescendant");
  suggestions = [];
  active = -1;
}

function setActive(i) {
  active = i;
  [...el.list.children].forEach((li, n) => li.setAttribute("aria-selected", String(n === i)));
  if (i >= 0) {
    el.input.setAttribute("aria-activedescendant", `opt-${i}`);
    el.list.children[i].scrollIntoView({ block: "nearest" });
  } else {
    el.input.removeAttribute("aria-activedescendant");
  }
}

/* Theme ---------------------------------------------------------------- */

const THEMES = ["auto", "light", "dark"];

function applyTheme(theme) {
  if (theme === "auto") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.setAttribute("data-theme", theme);
  el.theme.dataset.theme = theme;
  el.theme.setAttribute("aria-label", `Appearance: ${theme}. Change it.`);
  try { localStorage.setItem("boi-theme", theme); } catch { /* private mode */ }
}

/* Wiring --------------------------------------------------------------- */

el.form.addEventListener("submit", (e) => {
  e.preventDefault();
  if (active >= 0 && suggestions[active]) show(suggestions[active]);
  else show(el.input.value);
});

el.input.addEventListener("input", updateSuggestions);

el.input.addEventListener("keydown", (e) => {
  if (e.key === "Escape") return closeSuggestions();
  if (!suggestions.length) return;
  if (e.key === "ArrowDown") {
    e.preventDefault();
    setActive((active + 1) % suggestions.length);
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    setActive(active <= 0 ? suggestions.length - 1 : active - 1);
  }
});

el.list.addEventListener("mousedown", (e) => {
  const li = e.target.closest("li");
  if (li) {
    e.preventDefault();
    show(suggestions[[...el.list.children].indexOf(li)]);
  }
});

el.clear.addEventListener("click", () => {
  el.input.value = "";
  el.clear.hidden = true;
  el.submit.disabled = true;
  closeSuggestions();
  renderEmpty();
  setUrl("");
  el.input.focus();
});

document.addEventListener("click", (e) => {
  if (!el.form.contains(e.target)) closeSuggestions();
  const chip = e.target.closest("[data-word]");
  if (chip) show(chip.dataset.word);
  const swap = e.target.closest("[data-swap]");
  if (swap) {
    const reading = swap.dataset.swap;
    const word = el.input.value.trim().toLowerCase();
    const current = el.result.querySelector(".reading").textContent;
    const entry = shards.get(word[0]);
    if (entry) entry.then((shard) => {
      const [phones, readings] = shard[word].split("|");
      const reordered = [reading, ...readings.split(";").filter((r) => r !== reading)];
      if (reading !== current) renderResult(word, phones, reordered);
    });
  }
});

el.theme.addEventListener("click", () => {
  applyTheme(THEMES[(THEMES.indexOf(el.theme.dataset.theme) + 1) % THEMES.length]);
});

window.addEventListener("popstate", () => {
  const word = new URLSearchParams(location.search).get("w") || "";
  if (word) show(word, { push: false });
  else { el.input.value = ""; el.clear.hidden = true; el.submit.disabled = true; renderEmpty(); }
});

document.addEventListener("keydown", (e) => {
  if (e.key === "/" && document.activeElement !== el.input) {
    e.preventDefault();
    el.input.focus();
    el.input.select();
  }
});

async function boot() {
  try { applyTheme(localStorage.getItem("boi-theme") || "auto"); }
  catch { applyTheme("auto"); }

  const [idx, g] = await Promise.all([
    fetch("./data/index.json").then((r) => r.json()).catch(() => index),
    fetch("./data/gold.json").then((r) => r.json()).catch(() => ({})),
  ]);
  index = idx;
  gold = g;

  el.examples.querySelector(".chips").innerHTML = index.examples
    .map((w) => `<button type="button" class="chip" data-word="${w}">${w}</button>`).join("");
  el.count.textContent = index.words.toLocaleString("en-US");

  const word = new URLSearchParams(location.search).get("w");
  if (word) show(word, { push: false });
  else renderEmpty();
}

boot();
