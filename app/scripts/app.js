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
  gold: document.querySelector("#gold"),
  agree: document.querySelector("#agree"),
};

const shards = new Map();
let oov = null;       // promise for the browser pipeline
let oovReady = null;  // its resolved value, once it is in
let gold = {};
let index = { examples: [], words: 0, gold: 0, agree: 0 };
let active = -1;
let suggestions = [];
let current = null;   // what is on screen, so alternatives can swap in place

/** Tone of one Vietnamese syllable, from its combining mark. */
function toneOf(syllable) {
  for (const ch of syllable.normalize("NFD")) {
    if (TONE_MARKS[ch]) return TONE_MARKS[ch];
  }
  return "ngang";
}

async function loadOov() {
  if (!oov) {
    oov = Promise.all([
      import("./oov.js"),
      fetch("./data/tables.json").then((r) => r.json()),
      fetch("./data/words.txt").then((r) => r.text())
        .then((t) => new Set(t.split("\n"))),
    ]).then(([module, tables, known]) => {
      oovReady = { module, tables, known };
      return oovReady;
    });
  }
  return oov;
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
  el.result.innerHTML = `<p class="state">Nothing to read in <b>${escapeHtml(word)}</b>.
    Letters are what the generator works from, so try a word with some.</p>`;
  el.status.textContent = `${word}: nothing to read`;
}

function renderLoading() {
  el.examples.hidden = true;
  el.result.hidden = false;
  el.result.removeAttribute("data-fresh");
  el.result.innerHTML = '<div class="skeleton"></div>';
}

/** The derivation: the word, its sounds, and which sounds became which
 *  syllable. The grouping is the one the generator actually chose, read back
 *  out of the pipeline rather than drawn by eye.
 */
function trace(word, phones, spelled) {
  const sounds = (phones || "").split(" ").filter(Boolean);
  const stages = [
    ["The word", `<p class="stage-text">${escapeHtml(word)}</p>`],
    [spelled ? "Its letters, as sounds" : "Its sounds",
     sounds.length
       ? `<p class="stage-sounds">${sounds
           .map((ph, i) => `<span style="--j:${i}">${escapeHtml(ph)}</span>`).join("")}</p>`
       : `<p class="stage-text stage-text--quiet">no phones to show</p>`],
    ["Grouped into syllables", `<div class="stage-groups"></div>`],
  ];
  return `<section class="trace" data-playing>
    <ol class="stages">
      ${stages.map(([label, body], i) => `<li class="stage" style="--i:${i}">
        <h2>${label}</h2>${body}</li>`).join("")}
    </ol>
  </section>`;
}

/** Fill the last stage once the pipeline is loaded. */
function fillGrouping(word, phones, best, module, tables) {
  const host = el.result.querySelector(".stage-groups");
  if (!host) return;
  const list = (phones || "").split(" ").filter(Boolean);
  const collect = new Map();
  try {
    module.candidatesFromPhones(list, tables, 5,
                                module.alignVowels(word, list, tables), collect);
  } catch { return; }
  const groups = collect.get(best);
  if (!groups) {
    // A memorised reading has no slots behind it. Anything else means this
    // pipeline did not reproduce the shard's reading, which is a bug, so say
    // which of the two it is rather than claiming the flattering one.
    const memorised = Boolean(tables.lexicon[word.toLowerCase()]);
    host.innerHTML = `<p class="stage-text stage-text--quiet">${memorised
      ? "memorised, so there is no derivation to show"
      : "the derivation did not come back for this one"}</p>`;
    return;
  }
  host.innerHTML = groups.map((g, i) => `<div class="group" style="--j:${i}">
      <span class="group-phones">${g.phones.map(escapeHtml).join(" ")}</span>
      <span class="group-arrow" aria-hidden="true">${icon("chevron")}</span>
      <span class="group-vi"><b lang="vi">${escapeHtml(g.syllable)}</b>
        <span class="group-tone">${toneOf(g.syllable)}</span></span>
    </div>`).join("");
}

function renderResult(word, phones, readings, spelled = false, pieces = null) {
  current = { word, phones, readings, spelled, pieces };
  const [best, ...alts] = readings;
  const syllables = best.split(" ");
  const g = gold[word];

  let note = "";
  if (spelled) {
    note = `<p class="note note--spelled"><span class="note-label">Read off the
      spelling</span> CMUdict does not list this word</p>`;
  } else if (pieces) {
    note = `<p class="note note--spelled"><span class="note-label">Read as a
      compound</span> ${escapeHtml(pieces.join(" + "))}</p>`;
  } else if (g) {
    const matches = [g.vi, ...g.alt].includes(best);
    note = matches
      ? `<p class="note note--agree"><span class="note-label">Matches the reviewed reading</span></p>`
      : `<p class="note note--differ"><span class="note-label">Reviewed reading</span>
           <b>${escapeHtml(g.vi)}</b></p>`;
  }

  const rows = [
    ["From", spelled ? "the spelling, letter by letter"
      : pieces ? `${escapeHtml(pieces.join(" + "))}, from CMUdict` : "CMUdict"],
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
    ${trace(word, phones, spelled)}
    <details class="source">
      <summary>${icon("chevron")}More about this word</summary>
      <dl>${rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("")}</dl>
    </details>`;

  // Restart the one authored moment.
  el.result.removeAttribute("data-fresh");
  void el.result.offsetWidth;
  el.result.setAttribute("data-fresh", "");

  el.status.textContent = `${word} reads as ${best}, ${syllables.length} syllable${
    syllables.length === 1 ? "" : "s"}`;

  // The syllable grouping needs the browser pipeline, which loads behind the
  // first paint, so the reading is never held up waiting for it.
  loadOov().then(({ module, tables }) => {
    if (!current || current.word !== word) return;
    fillGrouping(word, phones, best, module, tables);
  });
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
  if (entry) {
    const [phones, readings] = entry.split("|");
    renderResult(w, phones, readings.split(";"));
  } else {
    // Not one of the precomputed words, so run the pipeline here instead.
    renderLoading();
    const { module, tables, known } = await loadOov();

    // A doubled letter is the commonest misspelling, and collapsing it often
    // lands on a word we already have: dissneeland reads as disneyland does.
    const plain = module.undoubled(w, (c) => c in shard);
    if (plain) {
      const [phones, readings] = shard[plain].split("|");
      renderResult(w, phones, readings.split(";"));
      return;
    }

    // A compound of known words beats reading the letters: poweroff is
    // power plus off, with real phones for each half.
    const pieces = module.splitInto(w, known);
    if (pieces) {
      const shardsFor = await Promise.all(pieces.map((p) => shardFor(p[0])));
      const phonesOf = (piece) => {
        const found = shardsFor[pieces.indexOf(piece)][piece];
        return found ? found.split("|")[0].split(" ") : null;
      };
      const phones = module.compoundPhones(pieces, phonesOf, tables);
      // The letters have to go with the phones or every rule keyed on
      // spelling reads blind: in phô mây sừn, not in phơ mây sa.
      const readings = module.candidatesFromPhones(
        phones, tables, 5, module.alignVowels(w, phones, tables));
      if (readings.length) {
        renderResult(w, phones.join(" "), readings, false, pieces);
        if (push) setUrl(w);
        return;
      }
    }

    const { phones, readings } = module.readUnknown(w, tables, 5);
    if (!readings.length) renderMissing(w);
    else renderResult(w, (phones || []).join(" "), readings, true);
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
  if (swap && current) {
    const reading = swap.dataset.swap;
    if (reading === current.readings[0]) return;
    const reordered = [reading, ...current.readings.filter((r) => r !== reading)];
    renderResult(current.word, current.phones, reordered,
                 current.spelled, current.pieces);
  }
});

el.theme.addEventListener("click", () => {
  applyTheme(THEMES[(THEMES.indexOf(el.theme.dataset.theme) + 1) % THEMES.length]);
});

// The wordmark is the route back to the empty state. It is a real link, so
// it opens in a new tab and reads as a link, but in this tab it resets in
// place rather than reloading the shards.
document.querySelector("#home").addEventListener("click", (e) => {
  if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
  e.preventDefault();
  goHome();
  el.input.focus();
});

function goHome() {
  current = null;
  el.input.value = "";
  el.clear.hidden = true;
  el.submit.disabled = true;
  closeSuggestions();
  renderEmpty();
  if (location.search) history.pushState({ word: "" }, "", location.pathname);
}

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

  // Each example shows its reading, so the empty page says what the tool does
  // before anyone types anything.
  el.examples.querySelector(".chips").innerHTML = index.examples
    .map(([w, vi]) => `<li><button type="button" class="chip" data-word="${escapeHtml(w)}">
        <span class="chip-en">${escapeHtml(w)}</span>
        <span class="chip-vi" lang="vi">${escapeHtml(vi)}</span></button></li>`).join("");
  // Read from the data rather than hard-coded, so the footer cannot go stale.
  el.count.textContent = index.words.toLocaleString("en-US");
  if (el.gold) el.gold.textContent = index.gold;
  if (el.agree) el.agree.textContent = index.agree;

  const word = new URLSearchParams(location.search).get("w");
  // The head's guard keeps the empty page hidden until something replaces
  // it. show() only hides the examples once its shard arrives, so the guard
  // is lifted after that and not as soon as show() is called; finally, so a
  // failed lookup cannot leave the empty page hidden for good.
  try {
    if (word) await show(word, { push: false });
    else renderEmpty();
  } finally {
    document.documentElement.classList.remove("opening-word");
  }

  // The derivation needs the pipeline, so fetch it once the page is up.
  requestIdleCallback?.(() => loadOov()) ?? setTimeout(loadOov, 1200);
}

boot();
