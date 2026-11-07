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
      if (hiatus(word, i, j, T)) out.push(["v", word[i]], ["v", word[i + 1]]);
      else out.push(["v", word.slice(i, j)]);
      i = j;
      continue;
    }

    if (i === 0 && word.slice(0, 2) in T.spell.wordInitial) {
      out.push(["c", [T.spell.wordInitial[word.slice(0, 2)]]]);
      i = 2;
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

/** spell._hiatus: two vowel letters that are no digraph are two syllables. */
function hiatus(word, i, j, T) {
  const pair = word.slice(i, j);
  if (pair.length !== 2 || pair in T.spell.digraphs || pair in T.spell.irregular) return false;
  return !(pair[0] === "i" && i > 0 && T.spell.glideIAfter.includes(word[i - 1]));
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
  const lengthened = word.length > 2 && word.endsWith("e")
    && !T.spell.vowels.includes(word[word.length - 2]);
  if (lengthened) word = word.slice(0, -1);
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
  let vowels = phones.filter((p) => T.spell.vowelPhones.includes(p.slice(0, -1))
    && /\d$/.test(p));
  // A syllabic consonant is a vowel phone with no vowel letter: the schwa of
  // -sm and -ble is written nowhere. Left out of the count, given an empty
  // group afterwards, so the letters before it still line up.
  const syllabic = groups.length < vowels.length && vowels.length > 1
    && vowels[vowels.length - 1] === "AH0"
    && ["M", "N", "L"].includes(phones[phones.length - 1])
    && !T.spell.vowels.includes(word[word.length - 1]);
  if (syllabic) vowels = vowels.slice(0, -1);
  while (groups.length < vowels.length) {
    let index = groups.findIndex((g) => g.length > 1 && !(g in T.spell.digraphs));
    if (index < 0) index = groups.findIndex((g) => g.length > 1);
    if (index < 0) return null;
    groups.splice(index, 1, ...groups[index].split(""));
  }
  // More vowel letters than phones means a silent one inside the word: the e
  // of improve before -ment. Only a lone e, never the first group.
  while (groups.length > vowels.length && groups.indexOf("e", 1) > 0) {
    groups.splice(groups.indexOf("e", 1), 1);
  }
  if (groups.length !== vowels.length) return null;
  if (syllabic) groups.push("");
  // A silent e lengthens the vowel before it: these is di, not dê.
  else if (lengthened && groups.length
           && groups[groups.length - 1].length === 1) {
    groups[groups.length - 1] += T.spell.lengthened;
  }
  // A word-final w belongs to the vowel before it: sâu and sờ nâu against
  // hê lô and vi đi ô. Appended after the counting so it cannot be split.
  if (groups.length && word.endsWith("w") && word.length > 1
      && T.spell.vowels.includes(word[word.length - 2])) {
    groups[groups.length - 1] += "w";
  }
  return groups;
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
    const prev = phones[i - 1] ?? "";
    const isVowel = (p) => T.syllabify.phoneVowels.includes(p.slice(0, -1));
    // Before a reduced vowel the vowel left behind takes its letter: ca mê ra.
    // Before a stressed one it stays ơ and the r opens the next syllable:
    // nơ rây, âu vờ ron. Not after a vowel, where a compound boundary
    // falls: pao ơ óp.
    if (phone === "ER0" && isVowel(next) && next.endsWith("0")) out.push("AH0", "R");
    else if (phone === "ER0" && (T.syllabify.frontVowels.includes(next.slice(0, -1))
                                 || (isVowel(next) && !isVowel(prev)))) {
      out.push("ER0", "R");
    } else out.push(phone);
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
          && !(right.letter === T.syllabify.tionLetters && right.final)
          && !right.yod
          && left.stress === "1" && ["", "0"].includes(right.stress)
          && !T.syllabify.keepsOffglide.includes(left.nucleus))
      // A doubled velar nasal stays the coda; phonemap reads the onset copy
      // as g, so singer is sinh gờ.
      // A nasal doubles when the reduced vowel after it is written with a
      // front letter: com men, lơn ninh, pham mi li, sinh gờ.
      || (T.syllabify.nasalCodas.includes(phone) && !left.coda.length
          && left.stress === "1" && ["", "0"].includes(right.stress)
          && nasalDoublesBefore(right));
    if (!ok) continue;
    // A doubled /tʃ/ is only the stop closure, so it returns as t.
    out[i] = { ...left, coda: [...left.coda, phone === "CH" ? "T" : phone],
               doubled: true };
    out[i + 1] = { ...out[i + 1], onsetDoubled: true };
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
        // A v after a tense vowel is unheard, as at the end of a word: live
        // is lai, so livestream is lai sờ trim. Only v; icecream keeps its s.
        const back = out[out.length - 1];
        if (phone === "V" && back && !back.coda.length
            && T.phonemap.tense.includes(back.nucleus)) continue;
        // A stop between a nasal coda and another consonant is unheard
        // rather than a syllable of its own: phờ ren li, like sen guých.
        const prev = out[out.length - 1];
        if (prev && T.syllabify.swallowedAfterNasal.includes(phone)
            && prev.coda.length
            && T.syllabify.nasalCodas.includes(prev.coda[prev.coda.length - 1])) {
          out[out.length - 1] = { ...prev, coda: [...prev.coda, phone] };
          continue;
        }
        out.push(slot({ onset: [phone], inserted: true }));
      }
      out.push({ ...s, onset: tail });
      continue;
    }
    out.push(s);
  }
  return out;
}

/** The reduced vowel alone decides: /ɛ/ and /ɚ/ always take the doubled
 *  nasal, /ɪ/ never does, and a schwa only where an i is written. */
function nasalDoublesBefore(right) {
  if (right.nucleus === "EH" || right.nucleus === "ER") return true;
  return right.nucleus === "AH"
    && (right.letter === "i" || right.letter === "y");
}

/** Whether each syllable follows a stressed one, once the shape is final. */
function markAfterStress(slots, T) {
  return slots.map((sl, i) => ({
    ...sl,
    afterStress: i > 0 && slots[i - 1].stress === "1",
    afterNasal: i > 0 && slots[i - 1].coda.length > 0
      && T.syllabify.nasalCodas.includes(slots[i - 1].coda.at(-1)),
    nextOnset: i + 1 < slots.length ? slots[i + 1].onset : [],
    nextNucleus: i + 1 < slots.length ? slots[i + 1].nucleus : "",
  }));
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
      out.push([markAfterStress(repaired, T), penalty + extra]);
    }
  }
  return out;
}

/* phonemap.py --------------------------------------------------------- */

function onsetOptions(phones, T, doubled, nucleus, stress) {
  // A doubled ŋ left the nasal behind as the previous coda, so the copy is
  // just g: sinh gờ. An ordinary onset ŋ keeps it, which singing needs.
  if (doubled && joinKey(phones) === "NG") return [["g", 0]];
  // /dʒ/ is gi, but đ before an unstressed back vowel: e đu cây sừn, sờ ke đùa.
  if (joinKey(phones) === "JH" && stress === "0"
      && T.phonemap.jhTakesD.includes(nucleus)) return T.phonemap.jhBeforeBack;
  if (!phones.length) return [["", 0]];
  const run = T.phonemap.onsetRuns[joinKey(phones)];
  if (run) return run;
  return T.phonemap.onset[phones[phones.length - 1]] ?? [["", 3]];
}

function nucleusOptions(phone, stress, closed, nextCoda, final, glide, onset,
                       letter, first, T, afterStress, nextOnset = []) {
  const P = T.phonemap;
  if (phone === "ER" && glide) return P.erAfterGlide;
  // ơ is what an er is read as; an or inside a word is not (information is
  // phô). A word-final -or is ơ again: đốc tơ, not đốc tô.
  if (phone === "ER" && letter === "o" && !final) return P.erSpelledOr;
  // /aɪ/ keeps its glide before every coda the gold has, but none is an m.
  // Before one it is a: tham.
  if (phone === "AY" && nextCoda[0] === "M") return P.ayBeforeM;
  // A stressed /ʌ/ is ă, but ơ before an s or a v: bớt, lớp. Not every
  // fricative: crush has one and takes ă.
  if (phone === "AH" && stress === "1" && ["S", "V"].includes(nextCoda[0])) {
    return P.ahBeforeSV;
  }
  if (phone === "AH" && ["1", "2"].includes(stress) && letter === "u" && nextCoda[0] === "L") {
    return P.ahSpelledUBeforeL;
  }
  // An unstressed u closed by an l takes the l as an a: sờ ke đùa. Stressed
  // it does not, which is cu and sờ cun.
  if (["UH", "UW"].includes(phone) && stress === "0"
      && joinKey(nextCoda) === "L") return P.uBeforeL;
  if (phone === "OW") {
    if (joinKey(nextCoda) === "L" && !final) return P.owFinal;
    // A final s or z closes it on paper and goes unheard: close and clothes
    // are both cờ lâu. post keeps pốt, its coda ending in a stop.
    if (final && nextCoda.length
        && ["S", "Z"].includes(nextCoda[nextCoda.length - 1])) return P.owFinal;
    // A word-initial stressed o before a v is over-: âu vơ. okay keeps ô cây.
    if (!closed && first && !onset.length && stress !== "0"
        && joinKey(nextOnset) === "V") return P.owFinal;
    // âu only where a w is written: sâu, pho lâu against hê lô, vi đi ô.
    if (!closed) return final && (letter || "").includes("w") ? P.owFinal : P.owMid;
  }
  // -ese is ít: chai nít, việt nam mít. The plain e separates it from chi
  // and pờ li, whose ee and ea keep their z silent.
  // The a of -ature is ây: tem pơ rây chờ. Before anything but that /tʃ/
  // it is read as written, which is what paranoid needs for pa ra noi.
  if (phone === "AH" && stress === "0" && letter === "a" && !closed
      && nextOnset.at(-1) === "CH") return P.aBeforeTure;
  // -ious is ợt: con sợt, đi li sợt. Its letters are iou, which no other
  // ending gives, so the s closing it is the only other condition.
  if (phone === "AH" && letter === "iou" && final
      && joinKey(nextCoda) === "S") return P.iousEnding;
  // -ese is a suffix, so it cannot be the whole word: these keeps di.
  if (phone === "IY" && letter.replace(T.spell.lengthened, "") === "e" && final
      && !first && ["Z", "S"].includes(joinKey(nextCoda))) return P.eseEnding;
  // A single plain vowel letter takes its Vietnamese value when the syllable
  // is stressed or closed: en and pê in encyclopedia, but i ven in event.
  // A word-initial open one is a prefix read as the English letter name.
  // Not before a velar nasal: eleven gold rows read i there whatever letter
  // is written, so english is inh lích.
  if (["IH", "IY"].includes(phone) && P.singleLetters.includes(letter)
      && nextCoda[0] !== "NG"
      && (["1", "2"].includes(stress) || closed) && !(first && !closed)) {
    const byLetter = P.schwaByLetter[letter];
    if (byLetter) return closed ? byLetter[1] : byLetter[0];
  }
  // /ɛ/ written ea and closed by a d is ê: đết lai, hết phôn.
  if (phone === "EH" && letter === "ea" && joinKey(nextCoda) === "D") {
    return P.ehEaBeforeD;
  }
  // A reduced vowel closed by m is ừm: dừm, từm. tone gives it the huyền.
  // ừm only where the m is syllabic or written with an e: dừm, từm, lừm.
  // A plain letter is read as itself, which keeps album at ao bum.
  if (phone === "AH" && stress === "0" && joinKey(nextCoda) === "M" && final
      && ["", "e"].includes(letter)) {
    return P.ahBeforeM;
  }
  // /ɑ/ takes the letter it is written with: com men and xóp against
  // ma két tinh and gia va. An aw is o too: raw is ro like law.
  if (phone === "AA" && (letter === "o" || letter === "aw")) return P.aaSpelledO;
  // /eɪ/ before an s is ây with the s unheard: phây búc, đa ta bây.
  if (phone === "EY" && joinKey(nextCoda) === "S") return P.eyBeforeS;
  // /æ/ is a, but e when a d closes the syllable: bét, sen, đít ni len.
  if (phone === "AE" && closed && nextCoda.length
      && nextCoda[nextCoda.length - 1] === "D") return P.aeBeforeD;
  if (phone === "AH" && stress === "0") {
    // -ment is ừn after a stressed syllable and men after a reduced one.
    if (afterStress && nextCoda[0] === "N" && P.singleLetters.includes(letter)
        && closed) {
      return P.schwaBeforeN;
    }
    const byLetter = letter && P.schwaByLetter[letter[0]];
    // -ate is ết: tem pờ lết, a cu rết. -age is not, so the t has to be
    // there; i mịt and mét sịt take their coda's reading instead.
    if (letter === "a" + T.spell.lengthened && joinKey(nextCoda) === "T") {
      return P.longABeforeT;
    }
    if (letter.endsWith(T.spell.lengthened) && P.longByLetter[letter[0]]) {
      return P.longByLetter[letter[0]];
    }
    if (!closed) return byLetter ? byLetter[0] : P.schwaOpen;
    // Before a coda n the letter decides: development is lắp men, not mon.
    if (["N", "M"].includes(nextCoda[0]) && P.singleLetters.includes(letter)) {
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

function codaOptions(phones, nucleus, schwa, vowel, T, doubled, reduced) {
  const P = T.phonemap;
  if (!phones.length) return [["", 0]];
  const key = joinKey(phones);
  // A final z goes unheard after a tense vowel (sai, chi, pờ li) but closes a
  // checked one: disneyland is đít ni.
  if (key === "Z" && vowel && !P.tense.includes(vowel)) return [["t", 0], ["", 1]];
  // After i a k is ch, unless it is a plain one closing a stressed syllable:
  // tích két, sờ pích cơ, nét phờ lích, mê ca ních against cờ líc, tíc tóc.
  if (nucleus === "i" && phones[0] === "K"
      && (doubled || reduced || phones.length > 1)) {
    return [["ch", 0], ["c", 1]];
  }
  // A real /ʃ/ closing an i is ch: english is lích. A doubled one is only
  // the closure, so delicious keeps đi lít sợt.
  if (key === "SH" && nucleus === "i" && !doubled) return [["ch", 0], ["t", 1]];
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
        && (nucleus !== "a" || (phones.length === 1 && phones[0] === "K"))) {
      out.push(["ch", penalty]);
    }
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
  // A reduced ừn takes huyền wherever it sits: sừn for -tion, mừn for a
  // -ment after a stressed syllable. The ư carries it, not the onset.
  if (s.nucleus === "AH" && s.stress === "0" && s.coda[0] === "N"
      && syl.nucleus === "ư"
      && (s.final || s.letter === T.syllabify.tionLetters)) return "huyen";
  // An open reduced syllable is huyền before a back vowel that a /j/ or its
  // own freed r opens: rì iu, âu vờ iu, âu vờ ron. Not before a front one.
  const opener = joinKey(s.nextOnset || []);
  if (s.stress === "0" && !syl.coda && T.tone.backVowels.includes(s.nextNucleus)
      && (opener === "Y" || (opener === "R" && s.nucleus === "ER"))) return "huyen";
  if (s.final) {
    if (s.stress === "0" && joinKey(s.coda) === "L"
        && ["AH", "UH", "UW"].includes(s.nucleus)) {
      return "huyen";          // -le/-al/-ule: gu gồ, mo đồ, đùa
    }
    // The huyền goes with the ư, not with the m: ao bum does not take it.
    if (s.nucleus === "AH" && s.stress === "0" && joinKey(s.coda) === "M"
        && syl.nucleus === "ư") {
      return "huyen";
    }
    // A final -er is mostly ờ; these are the consonants observed to take ơ.
    if (s.nucleus === "ER" && s.stress === "0") {
      const before = s.onset.length ? s.onset[s.onset.length - 1] : "";
      return T.tone.ngangBeforeEr.includes(before) ? "ngang" : "huyen";
    }
  }
  if (T.tone.stopCodas.includes(syl.coda)) {
    // -ious is glottalised like the other final fricatives: con sợt.
    if (s.final && (T.tone.nangCodas.includes(joinKey(s.coda))
                    || s.letter === "iou")) return "nang";
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
                        s.onset, s.letter, s.first, T, Boolean(s.afterStress),
                        s.nextOnset || []);
}

function slotOptions(s, T) {
  if (s.inserted) {
    return onsetOptions(s.onset, T, Boolean(s.onsetDoubled), s.nucleus, s.stress)
      .map(([o, p]) => [{ onset: o, glide: "", nucleus: T.syllabify.insertedNucleus,
                          coda: "", tone: "ngang" }, p])
      .slice(0, T.generate.perSlot);
  }

  const legal = new Map();
  const illegal = new Map();
  const schwa = s.nucleus === "AH" && s.stress === "0";
  // A /ju/ between vowels loses its /j/: reuse is rì iu, not ri diu.
  const hiatus = s.yod && joinKey(s.onset) === "Y" && s.nucleus === "UW" && !s.first;
  const onsets = hiatus ? [["", 0]]
    : onsetOptions(s.onset, T, s.onsetDoubled, s.nucleus, s.stress);
  for (const [onset, pOn] of onsets) {
    for (const [nucleus, offglide, pNu] of slotNucleusOptions(s, T)) {
      const codas = offglide
        ? [[offglide, s.coda.length ? 1 : 0]]
        : codaOptions(s.coda, nucleus, schwa, s.nucleus, T,
                      Boolean(s.doubled), s.stress === "0");
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
/** `collect`, when given, is filled with reading -> the slots that made it,
 *  so the page can show which phones became which syllable without guessing. */
export function candidatesFromPhones(phones, T, limit = 5, letters = null,
                                     collect = null) {
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
        if (!scored.has(text) || total < scored.get(text)) {
          scored.set(text, total);
          if (collect) {
            collect.set(text, slots.map((sl, n) => ({
              phones: [...sl.onset, sl.nucleus ? sl.nucleus + sl.stress : "",
                       ...sl.coda].filter(Boolean),
              syllable: render(syls[n], T),
              tone: syls[n].tone,
            })));
          }
        }
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
/** g2p.undoubled: the word with one doubled letter collapsed, if known. */
export function undoubled(word, known) {
  if (known(word)) return null;     // mousse is a word, not a misspelt mouse
  for (let i = 0; i + 1 < word.length; i += 1) {
    if (word[i] === word[i + 1]) {
      const candidate = word.slice(0, i) + word.slice(i + 1);
      if (known(candidate)) return candidate;
    }
  }
  const collapsed = word.replace(/(.)\1+/g, "$1");
  return collapsed !== word && known(collapsed) ? collapsed : null;
}

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

/**
 * g2p._known_parts: a word nobody lists as the known words in it, of
 * T.g2p.minKnown letters or more, and the letters between them. Null unless
 * the known words make up at least half the word.
 */
export function knownParts(word, known, T) {
  const out = [];
  let gap = "", i = 0;
  while (i < word.length) {
    let j = word.length;
    // A known word may not end inside a vowel digraph: shope out of shopee.
    while (j >= i + T.g2p.minKnown
           && (!known.has(word.slice(i, j)) || word.slice(j - 1, j + 1) in T.spell.digraphs)) j -= 1;
    if (j >= i + T.g2p.minKnown) {
      if (gap) out.push([gap, false]);
      out.push([word.slice(i, j), true]);
      gap = "";
      i = j;
    } else {
      gap += word[i];
      i += 1;
    }
  }
  if (gap) out.push([gap, false]);
  const knownLetters = out.reduce((n, [text, isWord]) => n + (isWord ? text.length : 0), 0);
  return 2 * knownLetters >= word.length && out.length > 1 ? out : null;
}

/**
 * g2p.parts and generate._hints: the phones of a word built from pieces, each
 * known piece said as it is alone and each gap read off its spelling, with
 * only the first keeping primary stress; and its letters, lined up piece by
 * piece, since across a join the spelling and the phones count vowels apart.
 */
export function partsPhones(word, pieces, phonesOf, T) {
  const phones = [], letters = [];
  let aligned = true;
  pieces.forEach(([text, isWord], n) => {
    // A compound is words said one after another, so each piece takes the
    // form it has alone. CMUdict lists and reduced first, as AH0 N D.
    const cited = isWord ? T.g2p.citation[text] : null;
    const said = (cited ? cited.split(" ") : isWord ? phonesOf(text) : spellPhones(text, T)) || [];
    const demoted = said.map((p) => (n && p.endsWith("1") ? p.replace("1", "2") : p));
    phones.push(...demoted);
    const groups = alignVowels(text, demoted, T);
    if (groups) letters.push(...groups);
    else aligned = false;
  });
  return { phones, letters: aligned ? letters : alignVowels(word, phones, T) };
}

/** Read a word the shards do not have, off its spelling. */
export function readUnknown(word, T, limit = 5) {
  const lower = word.toLowerCase();
  // A memorised reading is about the word, not its spelling: scheedule is
  // sờ ke đùa too.
  const fixed = T.lexicon[lower]
    ?? T.lexicon[undoubled(lower, (c) => c in T.lexicon) ?? ""];
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
      // A doubled letter is one sound whatever follows it, so its first
      // copy always goes back: offline is óp lin, not ô phờ phờ lin.
      if (n && run.length > 1
          && (run[0] === run[1] || !L.onsetClusters.includes(run.slice(-2)))) {
        run = run.slice(1);
      }
    }
    let coda = "";
    const lastOfGroup = place === vowelRuns(groups[groupIndex][1], T).length - 1;
    if (lastOfGroup && groupIndex + 1 < groups.length) {
      const tail = groups[groupIndex + 1][1];
      if (n === nuclei.length - 1) coda = tail;
      else if (tail.length > 1
               && (tail[0] === tail[1]
                   || !L.onsetClusters.includes(tail.slice(-2)))) {
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

/* Acronyms: letters.acronym_parts ---------------------------------------- */

function isSpelledRun(run, T, known) {
  const word = run.toLowerCase();
  if (T.letters.spellOut.includes(word)) return true;
  if (T.letters.asWord.includes(word)) return false;
  if (![...word].some((c) => T.letters.vowels.includes(c)) || run.length <= 2) return true;
  return run.length <= T.letters.acronymMax
    && (!known.has(word) || T.g2p.letterNamed.includes(word));
}

/** ["say", Vietnamese] and ["read", a word] parts, or null if not an acronym. */
export function acronymParts(word, T, known) {
  let head = "";
  let tail = word;
  if (!/^[A-Z0-9]{2,}$/.test(word) || /^[0-9]+$/.test(word)) {
    const match = word.match(/^([A-Za-z]*[a-z])([A-Z]{2,}[A-Z0-9]*)$/);
    if (!match) return null;
    [, head, tail] = match;
  }
  const parts = tail.match(/[A-Z]+|[0-9]+/g).map((run) => {
    if (/^[0-9]/.test(run)) {
      return ["say", [...run].map((d) => T.letters.digits[Number(d)]).join(" ")];
    }
    return run.length === 1 || isSpelledRun(run, T, known)
      ? ["say", [...run.toLowerCase()].map((c) => T.letters.names[c]).join(" ")]
      : ["read", run.toLowerCase()];
  });
  if (parts.every(([kind]) => kind === "read")) return null;
  if (head) parts.unshift(head.length === 1 ? ["say", T.letters.names[head]] : ["read", head.toLowerCase()]);
  return parts;
}
