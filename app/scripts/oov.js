// The pipeline, for words the precomputed shards do not have.
//
// Every table this reads is generated from the Python modules by
// scripts/build_tables.py; only the control flow below is written twice.
// tests/test_js_conformance.py runs this file against readings produced by
// the Python and fails the build on any disagreement, so the two cannot
// drift apart unnoticed.

const joinKey = (parts) => parts.join("+");

/* spell.py: English spelling -> ARPAbet ------------------------------- */

function graphemes(word, T) {
  const out = [];
  let i = 0;
  while (i < word.length) {
    const irregular = [4, 3]
      .map((n) => word.slice(i, i + n))
      .find((c) => c in T.spell.irregular);
    if (irregular) {
      out.push(["v", irregular]);
      i += irregular.length;
      continue;
    }

    if (T.spell.vowels.includes(word[i])) {
      let j = i;
      while (j < word.length && T.spell.vowels.includes(word[j])) j += 1;
      if (word[i] === "y" && j - i === 1 && j < word.length
          && T.spell.vowels.includes(word[j])) {
        out.push(["c", ["Y"]]);
        i += 1;
        continue;
      }
      // A w or y after a vowel belongs to the vowel group.
      if (j < word.length && T.spell.glideLetters.includes(word[j])
          && word.slice(i, j + 1) in T.spell.digraphs) {
        j += 1;
      }
      out.push(["v", word.slice(i, j)]);
      i = j;
      continue;
    }

    let matched = false;
    for (const size of [3, 2, 1]) {
      const piece = word.slice(i, i + size);
      if (piece in T.spell.consonants) {
        let phones = T.spell.consonants[piece];
        const next = word.slice(i + piece.length, i + piece.length + 1);
        // "" is a substring of everything, so a real letter is required or
        // egg comes out as G JH.
        if (piece in T.spell.soft && next && "eiy".includes(next)) {
          phones = [T.spell.soft[piece]];
        }
        // piece.length, not size: near the end of a word the slice is shorter.
        const doubled = piece.length === 1 && i > 0 && word[i - 1] === piece;
        if (!doubled) out.push(["c", phones]);
        i += piece.length;
        matched = true;
        break;
      }
    }
    if (!matched) i += 1;
  }
  return out;
}

function spellSyllables(parts, T) {
  const vowels = parts.map(([k], i) => (k === "v" ? i : -1)).filter((i) => i >= 0);
  if (!vowels.length) {
    const run = parts.map(([, p]) => p);
    if (!run.length) return [];
    return run.length > 1
      ? [[run.slice(0, -1), "", run.slice(-1)]]
      : [[run, "", []]];
  }
  const syllables = [];
  vowels.forEach((i, n) => {
    const start = n === 0 ? 0 : vowels[n - 1] + 1;
    let run = parts.slice(start, i).map(([, p]) => p);
    if (n && run.length > 1
        && !T.spell.onsetClusters.includes(joinKey(run.slice(0, 2).flat()))) {
      syllables[n - 1][2].push(...run.slice(0, 1));
      run = run.slice(1);
    }
    const coda = n === vowels.length - 1 ? parts.slice(i + 1).map(([, p]) => p) : [];
    syllables.push([run, parts[i][1], coda]);
  });
  return syllables;
}

const REDUCED = { EY: "IH", IY: "IY", AY: "IH", OW: "OW", UW: "UW" };

export function spellPhones(word, T) {
  word = [...word.toLowerCase()].filter((c) => /[a-z]/.test(c)).join("");
  if (!word) return null;

  const silentE = word.length > 2 && word.endsWith("e")
    && !T.spell.vowels.includes(word[word.length - 2]);
  const body = silentE ? word.slice(0, -1) : word;

  const syllables = spellSyllables(graphemes(body, T), T);
  if (!syllables.length) return null;

  const out = [];
  syllables.forEach(([onset, letters, coda], n) => {
    const stress = n === 0 ? "1" : (n === syllables.length - 1 ? "2" : "0");
    out.push(...onset.flat());

    const flatCoda = coda.flat();
    const open = !flatCoda.length || (silentE && n === syllables.length - 1);
    const base = letters ? letters[0] : "";

    let vowel;
    if (letters in T.spell.irregular) vowel = T.spell.irregular[letters];
    else if (letters === "ow") {
      vowel = T.spell.ow[(n === syllables.length - 1 && !flatCoda.length)
        ? "final" : "other"];
    } else if (letters in T.spell.digraphs) vowel = T.spell.digraphs[letters];
    else if (flatCoda.length && flatCoda[0] === "R" && base in T.spell.rColoured)
      vowel = T.spell.rColoured[base];
    else if (base in T.spell.single) vowel = T.spell.single[base][open ? 0 : 1];
    else vowel = "AH";

    if (stress === "0" && open && !(letters in T.spell.digraphs)
        && !(letters in T.spell.irregular)) {
      vowel = REDUCED[vowel] ?? vowel;
    }
    out.push(vowel + stress);
    out.push(...flatCoda);
  });
  return out;
}

/** spell.align_vowels: which letters each vowel phone was written with. */
export function alignVowels(word, phones, T) {
  word = [...word.toLowerCase()].filter((c) => /[a-z]/.test(c)).join("");
  if (word.length > 2 && word.endsWith("e")
      && !T.spell.vowels.includes(word[word.length - 2])) {
    word = word.slice(0, -1);
  }
  const groups = [];
  let i = 0;
  while (i < word.length) {
    if (T.spell.vowels.includes(word[i])) {
      let j = i;
      while (j < word.length && T.spell.vowels.includes(word[j])) j += 1;
      groups.push(word.slice(i, j));
      i = j;
    } else i += 1;
  }
  const vowels = phones.filter((p) => T.spell.vowelPhones.includes(p.slice(0, -1))
    && /\d$/.test(p));
  return groups.length === vowels.length ? groups : null;
}

/* syllabify.py -------------------------------------------------------- */

const slot = (o = {}) => ({
  onset: [], nucleus: "", coda: [], stress: "",
  glide: false, yod: false, inserted: false, final: false, first: false,
  letter: "", ...o,
});

function isOnsetRun(run, T) {
  if (run.length === 2 && ["L", "R"].includes(run[1])
      && T.syllabify.clusterHeads.includes(run[0])) return true;
  if (T.syllabify.sClusters.includes(joinKey(run))) return true;
  return T.syllabify.viOnsets.includes(joinKey(run))
    || joinKey(run) === "T+R" || joinKey(run) === "T+S";
}

function splitRun(run, left, T) {
  if (run.length && run[run.length - 1] === "W") return [run.slice(0, -1), run.slice(-1)];
  if (run.length && run[run.length - 1] === "Y") {
    const [coda, onset] = splitRun(run.slice(0, -1), left, T);
    return [coda, [...onset, "Y"]];
  }
  if (left && T.syllabify.offglideNuclei.includes(left[0])) {
    const [coda, onset] = splitRun(run, null, T);
    const keep = coda.length && T.syllabify.voiceless.includes(coda[coda.length - 1]);
    return [[], [...(keep ? coda : []), ...onset]];
  }
  if (T.syllabify.onsetRunsKeep.includes(joinKey(run))) return [[], run];
  for (let n = Math.min(2, run.length); n >= 1; n -= 1) {
    if (n === 1 || isOnsetRun(run.slice(-n), T)) {
      let coda = run.slice(0, run.length - n);
      let onset = run.slice(run.length - n);
      if (!coda.length && onset.length > 1 && left && ["1", "2"].includes(left[1])
          && !T.syllabify.tense.includes(left[0])) {
        coda = onset.slice(0, 1);
        onset = onset.slice(1);
      }
      return [coda, onset];
    }
  }
  return [run, []];
}

// syllabify._free_the_r: an unstressed ER before a vowel is a schwa plus an
// r onset, so camera is ca mê ra rather than ca mơ a.
function freeTheR(phones, T) {
  const out = [];
  phones.forEach((phone, i) => {
    const next = phones[i + 1] ?? "";
    // Only before a reduced vowel: a stressed one means a compound boundary.
    if (phone === "ER0" && T.syllabify.phoneVowels.includes(next.slice(0, -1))
        && next.endsWith("0")) out.push("AH0", "R");
    else out.push(phone);
  });
  return out;
}

function baseSlots(phones, letters, T) {
  phones = freeTheR(phones, T);
  const pairs = phones.map((p) => (/\d$/.test(p) ? [p.slice(0, -1), p.slice(-1)] : [p, ""]));
  const bare = pairs.map(([p]) => p);
  const vowels = bare.map((p, i) => (T.syllabify.phoneVowels.includes(p) ? i : -1))
    .filter((i) => i >= 0);

  if (!vowels.length) {
    if (!bare.length) return [];
    const [onset, coda] = bare.length > 1
      ? [bare.slice(0, -1), bare.slice(-1)] : [bare, []];
    return [slot({ onset, nucleus: "AH", coda, stress: "1", final: true })];
  }

  const onsets = [bare.slice(0, vowels[0])];
  const codas = [];
  for (let k = 0; k < vowels.length - 1; k += 1) {
    const [coda, onset] = splitRun(bare.slice(vowels[k] + 1, vowels[k + 1]),
                                   [bare[vowels[k]], pairs[vowels[k]][1]], T);
    codas.push(coda);
    onsets.push(onset);
  }
  codas.push(bare.slice(vowels[vowels.length - 1] + 1));

  return vowels.map((i, n) => {
    let onset = onsets[n];
    const glide = onset.length > 0 && onset[onset.length - 1] === "W";
    const yod = onset.length > 0 && onset[onset.length - 1] === "Y";
    // k takes the glide with it and spells qu; anything else leaves the w as
    // the onset on its own and peels off what came before: sweet is sờ guýt.
    if (glide && onset.length > 1 && onset[onset.length - 2] === "K") {
      onset = onset.slice(0, -1);
    }
    if (yod) onset = onset.slice(0, -1).length ? onset.slice(0, -1) : ["Y"];
    return slot({
      onset, nucleus: bare[i], coda: codas[n], stress: pairs[i][1],
      glide, yod, final: n === vowels.length - 1, first: n === 0,
      letter: letters && n < letters.length ? letters[n] : "",
    });
  });
}

function geminate(slots, T) {
  const out = slots.map((s) => ({ ...s, coda: [...s.coda] }));
  let changed = false;
  for (let i = 0; i < slots.length - 1; i += 1) {
    const left = out[i];
    const right = slots[i + 1];
    if (right.onset.length !== 1
        || T.syllabify.offglideNuclei.includes(left.nucleus)) continue;
    const phone = right.onset[0];
    // -ing doubles whatever is before it, -y only after a stressed syllable.
    const isIng = right.nucleus === "IH" && joinKey(right.coda) === "NG";
    const isY = right.nucleus === "IY" && !right.coda.length;
    const suffix = right.final && ["", "0", "2"].includes(right.stress)
      && (isIng || (isY && ["1", "2"].includes(left.stress)));
    // -tion is one piece wherever it sits, so its n doubles rather than
    // running off to the next syllable: in tơ nát sừn nồ.
    const tion = left.letter === T.syllabify.tionLetters && left.nucleus === "AH"
      && left.stress === "0" && phone === "N"
      && left.onset.length && T.syllabify.sibilants.includes(left.onset[left.onset.length - 1]);
    const codaKey = joinKey(left.coda);
    const ok = (tion && !left.coda.length)
      || (suffix && T.syllabify.geminates.includes(phone)
                && (codaKey === "" || codaKey === "R"))
      || (!left.coda.length && T.syllabify.voiceless.includes(phone)
          && left.stress === "1" && ["", "0"].includes(right.stress)
          && !T.syllabify.keepsOffglide.includes(left.nucleus));
    if (!ok) continue;
    out[i] = { ...left, coda: [...left.coda, phone] };
    changed = true;
  }
  return changed ? out : null;
}

function repair(slots, keepClusters, T) {
  const out = [];
  for (const s of slots) {
    if (s.onset.length > 1 && !T.syllabify.viOnsets.includes(joinKey(s.onset))) {
      if (keepClusters) { out.push(s); continue; }
      const pairKey = joinKey(s.onset.slice(-2));
      const tail = T.syllabify.viOnsets.includes(pairKey)
        ? s.onset.slice(-2) : s.onset.slice(-1);
      for (const phone of s.onset.slice(0, s.onset.length - tail.length)) {
        out.push(slot({ onset: [phone], inserted: true }));
      }
      out.push({ ...s, onset: tail });
      continue;
    }
    out.push(s);
  }
  return out;
}

function variants(phones, letters, T) {
  const base = baseSlots(phones, letters, T);
  if (!base.length) return [];
  const out = [];
  for (const [gem, basePenalty] of [[true, 0], [false, 1]]) {
    let shape = base;
    let penalty = basePenalty;
    if (gem) {
      const g = geminate(base, T);
      if (!g) continue;
      shape = g;
    } else if (!geminate(base, T)) {
      penalty = 0;
    }
    for (const [keep, extra] of [[false, 0], [true, 2]]) {
      const repaired = repair(shape, keep, T);
      if (keep && JSON.stringify(repaired) === JSON.stringify(repair(shape, false, T))) continue;
      out.push([repaired, penalty + extra]);
    }
  }
  return out;
}

/* phonemap.py --------------------------------------------------------- */

function onsetOptions(phones, T) {
  if (!phones.length) return [["", 0]];
  const run = T.phonemap.onsetRuns[joinKey(phones)];
  if (run) return run;
  return T.phonemap.onset[phones[phones.length - 1]] ?? [["", 3]];
}

function nucleusOptions(phone, stress, closed, nextCoda, final, glide, onset, letter, first, T) {
  const P = T.phonemap;
  if (phone === "ER" && glide) return P.erAfterGlide;
  // ơ is what an er is read as; an or inside a word is not (information is
  // phô). A word-final -or is ơ again: đốc tơ, not đốc tô.
  if (phone === "ER" && letter === "o" && !final) return P.erSpelledOr;
  if (phone === "OW") {
    if (joinKey(nextCoda) === "L" && !final) return P.owFinal;
    if (!closed) return final ? P.owFinal : P.owMid;
  }
  // A single plain vowel letter takes its Vietnamese value when the syllable
  // is stressed or closed: en and pê in encyclopedia, but i ven in event.
  // A word-initial open one is a prefix read as the English letter name.
  if (["IH", "IY"].includes(phone) && P.singleLetters.includes(letter)
      && (["1", "2"].includes(stress) || closed) && !(first && !closed)) {
    const byLetter = P.schwaByLetter[letter];
    if (byLetter) return closed ? byLetter[1] : byLetter[0];
  }
  if (phone === "AH" && stress === "0") {
    const byLetter = letter && P.schwaByLetter[letter[0]];
    if (!closed) return byLetter ? byLetter[0] : P.schwaOpen;
    // Before a coda n the letter decides: development is lắp men, not mon.
    if (nextCoda[0] === "N" && P.singleLetters.includes(letter)) {
      const byLetterN = P.schwaByLetter[letter];
      if (byLetterN) return byLetterN[1];
    }
    if (nextCoda[0] === "N"
        && onset.length && !P.fricatives.includes(onset[onset.length - 1])) {
      return P.schwaBeforeNStop;
    }
    const byCoda = P.schwaByCoda[nextCoda[0]];
    if (byCoda) return byCoda;
    return byLetter ? byLetter[1] : P.schwaClosed;
  }
  const table = closed ? P.nucleusClosed : P.nucleusOpen;
  return table[phone] ?? [["ơ", "", 3]];
}

function codaOptions(phones, nucleus, schwa, vowel, T) {
  const P = T.phonemap;
  if (!phones.length) return [["", 0]];
  const key = joinKey(phones);
  // A final z goes unheard after a tense vowel (sai, chi, pờ li) but closes a
  // checked one: disneyland is đít ni.
  if (key === "Z" && vowel && !P.tense.includes(vowel)) return [["t", 0], ["", 1]];
  if (key === "L") {
    if (P.back.includes(nucleus)) return schwa ? P.codaLBackSchwa : P.codaLBackStressed;
    return P.codaL[nucleus] ?? [["", 0]];
  }
  // A /tʃ/ coda is ch after i (sen guých) but t after a: match is mát.
  if (key === "CH" && nucleus === "a") return [[P.chCodaAfterA, 0], ["ch", 1]];
  const options = P.codaRuns[key] ?? P.coda[phones[0]] ?? P.coda[phones[phones.length - 1]]
    ?? [["", 2]];
  const out = [];
  for (const [coda, penalty] of options) {
    if (coda === "c" && P.chAfter.includes(nucleus)
        && (nucleus !== "a" || phones.length === 1)) out.push(["ch", penalty]);
    else if (coda === "ng" && P.nhAfter.includes(nucleus)) out.push(["nh", penalty]);
    else out.push([coda, penalty]);
    if (coda === "c" && nucleus === "i") out.push(["ch", penalty + 1]);
  }
  return out;
}

/* tone.py -------------------------------------------------------------- */

function toneOf(s, syl, T) {
  if (s.inserted) return "huyen";
  // -tion takes huyền wherever it sits, not only at the end of a word.
  if (s.nucleus === "AH" && s.stress === "0" && joinKey(s.coda) === "N"
      && s.onset.length && T.tone.sibilants.includes(s.onset[s.onset.length - 1])
      && (s.final || s.letter === T.syllabify.tionLetters)) return "huyen";
  if (s.final) {
    if (s.nucleus === "AH" && s.stress === "0" && joinKey(s.coda) === "L") {
      return "huyen";
    }
  }
  if (T.tone.stopCodas.includes(syl.coda)) {
    if (s.final && T.tone.nangCodas.includes(joinKey(s.coda))) return "nang";
    return "sac";
  }
  return "ngang";
}

/* vi.py: slots -> quốc ngữ --------------------------------------------- */

function spellOnset(syl, T) {
  if (syl.onset === "k") {
    if (syl.glide) return "qu";
    return "ieê".includes(syl.nucleus[0]) ? "k" : "c";
  }
  return syl.onset;
}

function spellGlide(syl, T) {
  if (!syl.glide || syl.onset === "k") return "";
  return T.vi.glideOBefore.includes(syl.nucleus[0]) ? "o" : "u";
}

function spellNucleus(syl) {
  if (syl.nucleus === "i" && syl.glide) return "y";
  if (!syl.coda) return ({ "iê": "ia", "uô": "ua", "ươ": "ưa" })[syl.nucleus] ?? syl.nucleus;
  return syl.nucleus;
}

function render(syl, T) {
  const nucleus = spellNucleus(syl);
  const i = T.vi.twoPart.includes(nucleus) ? 1 : 0;
  const marked = (nucleus.slice(0, i + 1) + T.vi.toneMarks[syl.tone]
    + nucleus.slice(i + 1)).normalize("NFC");
  return spellOnset(syl, T) + spellGlide(syl, T) + marked + syl.coda;
}

const isLegal = (syl, T) => (T.vi.legalCodas[syl.nucleus] ?? []).includes(syl.coda);

/* generate.py ---------------------------------------------------------- */

const KEEPS_YOD = ["P", "B", "M", "F", "V", "Y"];

function slotNucleusOptions(s, T) {
  if (s.yod && (!s.onset.length || KEEPS_YOD.includes(s.onset[s.onset.length - 1]))) {
    return s.nucleus === "UW" ? [["i", "u", 0]] : [["i", "", 0]];
  }
  const closed = s.coda.length > 0 && s.coda[0] !== "R";
  return nucleusOptions(s.nucleus, s.stress, closed, s.coda, s.final, s.glide,
                        s.onset, s.letter, s.first, T);
}

function slotOptions(s, T) {
  if (s.inserted) {
    return onsetOptions(s.onset, T)
      .map(([o, p]) => [{ onset: o, glide: "", nucleus: T.syllabify.insertedNucleus,
                          coda: "", tone: "ngang" }, p])
      .slice(0, T.generate.perSlot);
  }

  const legal = new Map();
  const illegal = new Map();
  const schwa = s.nucleus === "AH" && s.stress === "0";
  for (const [onset, pOn] of onsetOptions(s.onset, T)) {
    for (const [nucleus, offglide, pNu] of slotNucleusOptions(s, T)) {
      const codas = offglide
        ? [[offglide, s.coda.length ? 1 : 0]]
        : codaOptions(s.coda, nucleus, schwa, s.nucleus, T);
      for (const [coda, pCo] of codas) {
        let spelled = (onset === "g" && !s.glide && "ieê".includes(nucleus[0]))
          ? "gh" : onset;
        if (spelled === "gi" && nucleus[0] === "i") spelled = "d";
        const syl = { onset: spelled, glide: s.glide ? "w" : "", nucleus, coda,
                      tone: "ngang" };
        const penalty = pOn + pNu + pCo;
        const target = isLegal(syl, T) ? legal : illegal;
        const id = `${syl.onset}|${syl.glide}|${syl.nucleus}|${syl.coda}`;
        if (!target.has(id) || penalty < target.get(id)[1]) target.set(id, [syl, penalty]);
      }
    }
  }
  const pool = legal.size ? legal : illegal;
  return [...pool.values()].sort((a, b) => a[1] - b[1]).slice(0, T.generate.perSlot);
}

function score(syls, tablePenalty, structural, T) {
  let total = tablePenalty + structural;
  for (const s of syls) {
    if (T.vi.clusters.includes(s.onset)) total += T.rank.illegalOnset;
    if (!T.rank.rhymes.includes(`${s.nucleus}|${s.coda}`)) total += T.rank.unseenRhyme;
  }
  return total;
}

/** Ranked readings for phones the shards did not supply. */
export function candidatesFromPhones(phones, T, limit = 5, letters = null) {
  const scored = new Map();
  for (const [slots, structural] of variants(phones, letters, T)) {
    const options = slots.map((s) => slotOptions(s, T));
    if (options.some((o) => !o.length)) continue;
    const floor = options.reduce((sum, o) => sum + o[0][1], 0);

    const walk = (i, chosen, penalty) => {
      if (penalty > floor + T.generate.budget) return;
      if (i === options.length) {
        const syls = chosen.map((syl, n) => ({ ...syl, tone: toneOf(slots[n], syl, T) }));
        const text = syls.map((s) => render(s, T)).join(" ");
        const total = score(syls, penalty, structural, T);
        if (!scored.has(text) || total < scored.get(text)) scored.set(text, total);
        return;
      }
      for (const [syl, p] of options[i]) walk(i + 1, [...chosen, syl], penalty + p);
    };
    walk(0, [], 0);
  }
  // Ties break on the string itself, by code point, which is what Python's
  // sorted() does. localeCompare would order á before o and diverge.
  return [...scored.entries()]
    .sort((a, b) => a[1] - b[1] || (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0))
    .slice(0, limit)
    .map(([text]) => text);
}

// g2p.py's _MIN_PIECE. Anything shorter makes junk splits: shopee is not
// shop plus ee.
const MIN_PIECE = 3;

/**
 * Fewest, longest known words this word is made of, or null.
 * Mirrors g2p._split; tests/test_js_conformance.py pins the two together.
 */
export function splitInto(word, known) {
  const go = (i, depth) => {
    if (i === word.length) return [];
    if (depth > 3) return null;
    let best = null;
    for (let j = word.length; j >= i + MIN_PIECE; j -= 1) {
      const piece = word.slice(i, j);
      if (!known.has(piece)) continue;
      const rest = go(j, depth + 1);
      if (rest !== null && (best === null || rest.length + 1 < best.length)) {
        best = [piece, ...rest];
      }
    }
    return best;
  };
  const pieces = go(0, 1);
  return pieces && pieces.length > 1 ? pieces : null;
}

/** Phones for a split; only the first piece keeps primary stress. */
export function compoundPhones(pieces, phonesOf) {
  const out = [];
  pieces.forEach((piece, n) => {
    const phones = phonesOf(piece);
    if (!phones) return;
    for (const phone of phones) {
      out.push(n && phone.endsWith("1") ? phone.replace("1", "2") : phone);
    }
  });
  return out;
}

/** Read a word the shards do not have, off its spelling. */
export function readUnknown(word, T, limit = 5) {
  const fixed = T.lexicon[word.toLowerCase()];
  const phones = spellPhones(word, T);
  if (!phones) return { phones: null, readings: fixed ? [fixed] : [] };
  let readings = candidatesFromPhones(phones, T, limit, alignVowels(word, phones, T));
  if (fixed) readings = [fixed, ...readings.filter((r) => r !== fixed)].slice(0, limit);
  return { phones, readings };
}

/* letters.py: read the spelling with Vietnamese letter values -------- */

function vowelRuns(group, T) {
  const out = [];
  let i = 0;
  while (i < group.length) {
    let taken = false;
    for (const size of [2, 1]) {
      const piece = group.slice(i, i + size);
      if (piece.length === size && piece in T.letters.nucleus) {
        out.push(piece);
        i += size;
        taken = true;
        break;
      }
    }
    if (!taken) { out.push(group[i]); i += 1; }
  }
  return out;
}

function letterChunks(word, T) {
  const L = T.letters;
  const groups = [];
  let i = 0;
  while (i < word.length) {
    if (L.vowels.includes(word[i])) {
      let j = i;
      while (j < word.length && L.vowels.includes(word[j])) j += 1;
      if (j < word.length && L.glideLetters.includes(word[j])
          && word.slice(i, j + 1) in L.nucleus) j += 1;
      groups.push(["v", word.slice(i, j)]);
      i = j;
    } else {
      let j = i;
      while (j < word.length && !L.vowels.includes(word[j])) j += 1;
      groups.push(["c", word.slice(i, j)]);
      i = j;
    }
  }

  const nuclei = [];
  groups.forEach(([kind, text], n) => {
    if (kind !== "v") return;
    vowelRuns(text, T).forEach((piece, k) => nuclei.push([n, k, piece]));
  });
  if (!nuclei.length) return word ? [[word, "", ""]] : [];

  return nuclei.map(([groupIndex, place, piece], n) => {
    let run = "";
    if (place === 0 && groupIndex && groups[groupIndex - 1][0] === "c") {
      run = groups[groupIndex - 1][1];
      if (n && run.length > 1 && !L.onsetClusters.includes(run.slice(-2))) {
        run = run.slice(1);
      }
    }
    let coda = "";
    const lastOfGroup = place === vowelRuns(groups[groupIndex][1], T).length - 1;
    if (lastOfGroup && groupIndex + 1 < groups.length) {
      const tail = groups[groupIndex + 1][1];
      if (n === nuclei.length - 1) coda = tail;
      else if (tail.length > 1 && !L.onsetClusters.includes(tail.slice(-2))) {
        coda = tail.slice(0, 1);
      }
    }
    return [run, piece, coda];
  });
}

function letterOnset(lettersRun, nucleus, T) {
  if (!lettersRun) return "";
  for (const size of [2, 1]) {
    if (lettersRun.length < size) continue;
    const piece = lettersRun.slice(-size);
    if (piece in T.letters.onset) {
      if (size === 1 && piece in T.letters.fronted && nucleus && "iê".includes(nucleus[0])) {
        return T.letters.fronted[piece];
      }
      return T.letters.onset[piece];
    }
  }
  return "";
}

/** Read a word as if its letters were Vietnamese. The second reading. */
export function readLetters(word, T) {
  const L = T.letters;
  word = [...word.toLowerCase()].filter((c) => /[a-z]/.test(c)).join("");
  if (!word) return null;
  if (word.length > 2 && word.endsWith("e") && !L.vowels.includes(word[word.length - 2])
      && !"lr".includes(word[word.length - 2])) {
    word = word.slice(0, -1);
  }

  const syllables = [];
  for (let [onsetLetters, vowelLetters, codaLetters] of letterChunks(word, T)) {
    while (onsetLetters.length > 1 && !(onsetLetters in L.onset)) {
      const head = onsetLetters[0];
      onsetLetters = onsetLetters.slice(1);
      const spelled = L.onset[head] ?? "";
      if (spelled) {
        syllables.push({ onset: spelled, glide: "", nucleus: "ơ", coda: "", tone: "huyen" });
      }
    }
    let [nucleus, offglide] = L.nucleus[vowelLetters]
      ?? L.nucleus[vowelLetters.slice(0, 1)] ?? ["ơ", ""];
    const onset = letterOnset(onsetLetters, nucleus, T);
    if (codaLetters.slice(0, 1) === "r" && nucleus in L.rColoured) {
      nucleus = L.rColoured[nucleus];
      offglide = "";
      codaLetters = codaLetters.slice(1);
    }
    let coda = offglide || L.coda[codaLetters] || L.coda[codaLetters.slice(0, 1)] || "";
    if (coda === "c" && "aê".includes(nucleus)) coda = "ch";
    else if (coda === "ng" && "iê".includes(nucleus)) coda = "nh";

    let syl = { onset, glide: "", nucleus, coda, tone: "ngang" };
    if (!isLegal(syl, T)) {
      const fallback = { ...syl, coda: offglide };
      syl = isLegal(fallback, T) ? fallback : { ...syl, coda: "" };
    }
    if (syl.coda && L.stops.includes(syl.coda)) syl.tone = "sac";
    syllables.push(syl);
  }
  return syllables.length ? syllables.map((s) => render(s, T)).join(" ") : null;
}
