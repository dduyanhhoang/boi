// Review tool for data/review/sheet_001.csv. Shows one word at a time with
// the generator's candidates, keeps answers in localStorage so the sheet can
// be done in sittings, and exports a CSV that merge_review.py accepts.
//
// It never decides anything: every reading here comes from the generator or
// from what the reviewer types.

import { readLetters } from "../scripts/oov.js";

const STORE = "boi-review-001";
const el = (id) => document.getElementById(id);

let rows = [];
let tables = null;
let at = 0;
let answers = {};

try { answers = JSON.parse(localStorage.getItem(STORE) || "{}"); } catch { answers = {}; }

const save = () => {
  try { localStorage.setItem(STORE, JSON.stringify(answers)); } catch { /* full */ }
};

function parseCsv(text) {
  const out = [];
  let row = [], field = "", quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') { field += '"'; i += 1; }
      else if (c === '"') quoted = false;
      else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ",") { row.push(field); field = ""; }
    else if (c === "\n") { row.push(field); out.push(row); row = []; field = ""; }
    else if (c !== "\r") field += c;
  }
  if (field || row.length) { row.push(field); out.push(row); }
  const head = out.shift();
  return out.filter((r) => r.length === head.length)
    .map((r) => Object.fromEntries(head.map((h, i) => [h, r[i]])));
}

const csvCell = (v) => (/[",\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v);

/* Rendering ----------------------------------------------------------- */

function choicesFor(row) {
  const seen = new Set();
  const out = [];
  const add = (reading, note) => {
    if (!reading || seen.has(reading)) return;
    seen.add(reading);
    out.push({ reading, note });
  };
  add(row.vi_form, "generated");
  for (const alt of row.alt_forms.split(";")) add(alt, "");
  if (tables) add(readLetters(row.word, tables), "as letters");
  return out.slice(0, 5);
}

function show() {
  const remaining = rows.filter((r) => !answers[r.word]);
  el("count").textContent = `${rows.length - remaining.length} / ${rows.length}`;
  el("fill").style.width = `${((rows.length - remaining.length) / rows.length) * 100}%`;

  if (at >= rows.length) {
    el("card").hidden = true;
    el("done").hidden = false;
    return;
  }
  el("card").hidden = false;
  el("done").hidden = true;

  const row = rows[at];
  el("tags").textContent = row.tags.split(";").filter(Boolean).join(" · ") || "—";
  el("word").textContent = row.word;
  el("phones").textContent = row.arpabet;
  el("error").hidden = true;
  el("custom").value = answers[row.word]?.custom ?? "";

  const picked = answers[row.word]?.vi_form;
  el("choices").innerHTML = choicesFor(row).map((c, i) => `
    <li><button type="button" data-reading="${c.reading.replace(/"/g, "&quot;")}"
      ${c.reading === picked ? 'aria-current="true"' : ""}>
      <kbd>${i + 1}</kbd><span lang="vi">${c.reading}</span>
      ${c.note ? `<span class="note">${c.note}</span>` : ""}</button></li>`).join("");
  if (picked) {
    const current = el("choices").querySelector('[aria-current="true"]');
    if (current) current.style.borderColor = "var(--accent)";
  }
}

function answer(reading, custom = false) {
  const row = rows[at];
  answers[row.word] = {
    vi_form: reading,
    status: reading === row.vi_form ? "approved" : "corrected",
    custom: custom ? reading : "",
  };
  save();
  at += 1;
  show();
}

/* Wiring -------------------------------------------------------------- */

el("choices").addEventListener("click", (e) => {
  const button = e.target.closest("[data-reading]");
  if (button) answer(button.dataset.reading);
});

el("other").addEventListener("submit", (e) => {
  e.preventDefault();
  const value = el("custom").value.trim();
  if (!value) return;
  answer(value, true);
});

el("skip").addEventListener("click", () => { at += 1; show(); });
el("back").addEventListener("click", () => { at = Math.max(0, at - 1); show(); });

document.addEventListener("keydown", (e) => {
  if (document.activeElement === el("custom")) return;
  const buttons = [...el("choices").querySelectorAll("[data-reading]")];
  if (/^[1-5]$/.test(e.key) && buttons[+e.key - 1]) {
    e.preventDefault();
    buttons[+e.key - 1].click();
  } else if (e.key === "Enter" && buttons[0]) {
    e.preventDefault();
    buttons[0].click();
  } else if (e.key.toLowerCase() === "s") {
    e.preventDefault();
    el("skip").click();
  }
});

function exportCsv() {
  const head = ["id", "word", "arpabet", "vi_form", "alt_forms", "vi_native",
                "tags", "confidence", "status"];
  const body = rows.map((r) => {
    const a = answers[r.word];
    const out = { ...r };
    if (a) {
      out.vi_form = a.vi_form;
      out.status = a.status;
      out.confidence = out.confidence || "h";
    }
    return head.map((h) => csvCell(out[h] ?? "")).join(",");
  });
  const blob = new Blob([head.join(",") + "\n" + body.join("\n") + "\n"],
                        { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "sheet_001.csv";
  a.click();
  URL.revokeObjectURL(a.href);
}
el("export").addEventListener("click", exportCsv);
el("export2").addEventListener("click", exportCsv);

const THEMES = ["auto", "light", "dark"];
el("theme").addEventListener("click", () => {
  const next = THEMES[(THEMES.indexOf(el("theme").dataset.theme) + 1) % THEMES.length];
  if (next === "auto") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.setAttribute("data-theme", next);
  el("theme").dataset.theme = next;
  try { localStorage.setItem("boi-theme", next); } catch { /* private mode */ }
});

async function boot() {
  try {
    const saved = localStorage.getItem("boi-theme") || "auto";
    if (saved !== "auto") document.documentElement.setAttribute("data-theme", saved);
    el("theme").dataset.theme = saved;
  } catch { /* private mode */ }

  const [text, loaded] = await Promise.all([
    fetch("../data/review.csv").then((r) => r.text()),
    fetch("../data/tables.json").then((r) => r.json()).catch(() => null),
  ]);
  tables = loaded;
  rows = parseCsv(text);
  at = rows.findIndex((r) => !answers[r.word]);
  if (at < 0) at = rows.length;
  show();
}

const toolbar = document.querySelector(".toolbar");
addEventListener("scroll", () => toolbar.classList.toggle("scrolled", scrollY > 0), { passive: true });

boot();
