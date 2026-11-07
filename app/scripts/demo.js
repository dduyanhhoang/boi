/**
 * The empty page's demonstration: an example word is taken through the real
 * pipeline on screen, its sounds and then its syllables, and the next example
 * follows, round and round.
 *
 * The grouping is the browser pipeline's own (candidatesFromPhones with a
 * collect map, as the derivation on a result uses), so what is shown is what
 * the generator does. Each step is a short fade or an 8px rise, the page's
 * only kinds of motion.
 *
 * It pauses while the pointer or keyboard focus is on it, while it is out of
 * view, while the tab is hidden, and when the visitor presses its pause
 * button, which WCAG 2.2.2 asks of anything that moves for more than five
 * seconds. Under reduced motion it starts paused, on a finished word.
 */

const STEP = { word: 400, phone: 60, settle: 300, group: 220, hold: 2600, out: 200 };

const escapeHtml = (s) => s.replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

/** Each example as { word, reading, groups }, dropping any the pipeline cannot group. */
function derive(examples, { module, tables }) {
  return examples.flatMap(([word, reading, phones]) => {
    const list = (phones || "").split(" ").filter(Boolean);
    const collect = new Map();
    try {
      module.candidatesFromPhones(list, tables, 5, module.alignVowels(word, list, tables), collect);
    } catch { return []; }
    const groups = collect.get(reading);
    return groups ? [{ word, reading, groups }] : [];
  });
}

function frame({ word, groups }, toneOf) {
  let p = 0;
  const columns = groups.map((g, i) => `<span class="demo-group" style="--g:${i}">
      <span class="demo-phones">${g.phones.map((ph) =>
        `<i style="--p:${p++}">${escapeHtml(ph)}</i>`).join(" ")}</span>
      <b class="demo-syl" lang="vi">${escapeHtml(g.syllable)}</b>
      <small class="demo-tone">${toneOf(g.syllable)}</small>
    </span>`).join("");
  return `<span class="demo-word">${escapeHtml(word)}</span>
    <span class="demo-groups">
      <span class="demo-group demo-caps"><span>sounds</span><span>syllables</span><span>tones</span></span>
      ${columns}
    </span>`;
}

export function startDemo(host, examples, pipeline, { toneOf, onPick }) {
  const link = host.querySelector(".demo-frame");
  const toggle = host.querySelector(".demo-toggle");
  const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
  let stopped = still, over = false, items = [], at = 0;

  const paused = () => stopped || over || document.hidden || !host.offsetParent;
  const wait = async (ms) => {
    for (let left = ms; left > 0;) {
      await new Promise((r) => setTimeout(r, 100));
      if (!paused()) left -= 100;
    }
  };

  function setStopped(on) {
    stopped = on;
    toggle.setAttribute("aria-pressed", String(on));
    toggle.setAttribute("aria-label", on ? "Play the demonstration" : "Pause the demonstration");
  }

  function put(item, finished) {
    link.className = "demo-frame" + (finished ? " is-sounds is-groups" : "");
    link.href = `?w=${encodeURIComponent(item.word)}`;
    link.setAttribute("aria-label", `${item.word} reads ${item.reading}. Open it.`);
    link.innerHTML = frame(item, toneOf);
  }

  async function play() {
    for (;;) {
      const item = items[at];
      put(item, stopped);
      await wait(STEP.word);
      link.classList.add("is-sounds");
      const phones = item.groups.reduce((n, g) => n + g.phones.length, 0);
      await wait(phones * STEP.phone + STEP.settle);
      link.classList.add("is-groups");
      await wait(item.groups.length * STEP.group + STEP.hold);
      link.classList.add("is-out");
      await wait(STEP.out);
      at = (at + 1) % items.length;
    }
  }

  host.addEventListener("pointerenter", () => { over = true; });
  host.addEventListener("pointerleave", () => { over = false; });
  host.addEventListener("focusin", (e) => { over = e.target === link; });
  host.addEventListener("focusout", () => { over = false; });
  toggle.addEventListener("click", () => setStopped(!stopped));
  link.addEventListener("click", (e) => {
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
    e.preventDefault();
    onPick(items[at].word);
  });

  pipeline.then((loaded) => {
    items = derive(examples, loaded);
    if (!items.length) return;
    setStopped(still);
    host.hidden = false;
    play();
  });
}
