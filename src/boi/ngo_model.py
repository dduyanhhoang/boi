"""Ngo et al. 2018, implemented from the paper.

*A Phonology-Augmented Statistical Framework for Machine Transliteration using
Limited Linguistic Resources*, Ngo, Chen, Nguyen, Ma and Li, IEEE/ACM TASLP
2018 (arXiv:1810.03184). Three steps, section III:

1. Pseudo-syllable formulation. Every grapheme of the source word gets a label
   from {O, N, Cd, ON, X}: onset, nucleus, coda, onset-with-an-epenthetic-
   nucleus, or excluded. The labels group the letters into pseudo-syllables
   that obey the target language's phonotactics. Decoded with an n-gram over a
   window of letters, Eq. 5, with the consonant/vowel back-off of Eq. 6.
2. Pseudo-syllable to phoneme mapping, Eq. 8: p(e | s, v), the target phoneme
   given the source graphemes and source phonemes of that sub-syllabic unit.
3. Lexical tone assignment, Eq. 9: p(t_k | t_k-1, onset, nucleus, coda).

The paper's own worked example is DISNEYLAND, Figure 4, which it formulates
as D-I / S-@: / N-EY / L-A-N and reads đi sờ ni len. That is the test this
implementation has to pass.

Nothing here is a port of their code; it is written from the paper. Their own
code is in third_party/ngo and does not reproduce their published output.
"""

import collections
import itertools

from . import ngo

LABELS = ("O", "N", "Cd", "ON", "X")
VOWEL_LETTERS = "aeiouy"
# The nucleus their ON label inserts (Figure 4: a schwa).
EPENTHETIC = "@:"


def target_slots(line):
    """Their X-SAMPA reading -> [(role, token), ...] in order.

    role is O, N or Cd, which is the structure a pseudo-syllable must match.
    """
    out = []
    for syllable in line.strip().split(" . "):
        parts = [p for p in syllable.split() if not p.startswith("_")]
        if not parts:
            return None
        body = list(parts)
        if len(body) > 1 and body[0] in ngo.ONSETS:
            out.append(("O", body.pop(0)))
        if not body or body[0] not in ngo.NUCLEI:
            return None
        out.append(("N", body.pop(0)))
        for token in body:
            if token not in ngo.CODAS:
                return None
            out.append(("Cd", token))
    return out


def target_tones(line):
    """Their reading -> the tone marker of each syllable, in order.

    target_slots drops these with the rest of the _-prefixed tokens, because
    the slot sequence is about structure. Eq. 9 needs them back.
    """
    out = []
    for syllable in line.strip().split(" . "):
        marks = [p for p in syllable.split() if p.startswith("_")]
        out.append(marks[-1] if marks else "_1")
    return out


def derive_labels(word, slots):
    """The label per letter whose pseudo-syllables match those slots, or None.

    Section III-A-3. The paper searches label combinations and rejects any
    partial sequence that cannot form valid pseudo-syllables; the same search
    is done here as a walk over (letter, slot) with memoisation, which is the
    same thing without the wasted branches.
    """
    n, m = len(word), len(slots)
    seen = {}

    def walk(i, j, joining):
        """Letters from i on, slots from j on. joining: last letter took slot j-1."""
        if i == n:
            return [] if j == m else None
        key = (i, j, joining)
        if key in seen:
            return seen[key]

        letter, result = word[i], None
        # Try to use the letter before dropping it: the paper's Figure 4
        # excludes only the final D, and keeps both E and Y as one nucleus.
        if j < m:
            role = slots[j][0]
            vowel = letter in VOWEL_LETTERS
            # The letter fills this slot. A nucleus may be spelled with more
            # than one letter (Figure 4 joins E and Y), so N can repeat.
            if (role == "N") == vowel:
                rest = walk(i + 1, j + 1, True)
                if rest is not None:
                    result = [role] + rest
            # ON: a consonant takes an onset and inserts a nucleus after it.
            if result is None and role == "O" and not vowel \
                    and j + 1 < m and slots[j + 1] == ("N", EPENTHETIC):
                rest = walk(i + 1, j + 2, False)
                if rest is not None:
                    result = ["ON"] + rest

        # Join the previous slot: two letters, one nucleus.
        if result is None and joining and j > 0 and slots[j - 1][0] == "N" \
                and letter in VOWEL_LETTERS:
            rest = walk(i + 1, j, True)
            if rest is not None:
                result = ["N"] + rest

        # X last: a letter is excluded only when it cannot be placed.
        if result is None:
            rest = walk(i + 1, j, False)
            if rest is not None:
                result = ["X"] + rest

        seen[key] = result
        return result

    return walk(0, 0, False)


# --- training -------------------------------------------------------------

def training_pairs():
    """(word, letter-aligned source phones, target slots, labels) per example."""
    words, phones = [], []
    for line in open(ngo.DATA / "large_test.lex", encoding="utf-8"):
        if "\t\t" in line:
            word, aligned = line.strip().split("\t\t")
            words.append(word)
            phones.append(aligned.split())
    lines = open(ngo.DATA / "large_test.vie", encoding="utf-8").read().splitlines()

    out = []
    for word, aligned, line in zip(words, phones, lines):
        if len(aligned) != len(word):
            continue
        slots = target_slots(line)
        if not slots:
            continue
        labels = derive_labels(word, slots)
        if labels:
            out.append((word, aligned, slots, labels, target_tones(line)))
    return out


def _window(word, i, size=2):
    """The letters around position i, padded, for the label n-gram."""
    out = []
    for j in range(i - size, i + size + 1):
        out.append(word[j] if 0 <= j < len(word) else "#")
    return out


def _class_of(letter):
    if letter == "#":
        return "#"
    return "V" if letter in VOWEL_LETTERS else "C"


def _backoffs(window, centre):
    """Eq. 6: the n-gram, then letters replaced by C/V outwards, then shorter.

    Yielded most specific first; the caller takes the first that was seen.
    """
    size = len(window) // 2
    for drop in range(size + 1):
        kept = window[drop:len(window) - drop] if drop else list(window)
        offset = drop
        for generalise in range(len(kept) + 1):
            form = list(kept)
            for k in range(len(form)):
                if abs(k + offset - centre) > len(kept) // 2 - generalise:
                    form[k] = _class_of(form[k])
            yield tuple(form), len(kept)


def units_from_labels(word, aligned, labels):
    """Labels -> pseudo-syllables, each a dict of grapheme and phone groups.

    Section III-A-ii. O opens a syllable; ON opens one and inserts the
    epenthetic nucleus; adjacent N letters join into one nucleus; X is
    dropped.
    """
    syllables, current = [], None

    def fresh():
        return {"og": "", "op": [], "ng": "", "np": [], "cg": "", "cp": [],
                "epenthetic": False}

    for i, label in enumerate(labels):
        if label == "X":
            continue
        if label in ("O", "ON"):
            current = fresh()
            syllables.append(current)
            current["og"], current["op"] = word[i], [aligned[i]]
            if label == "ON":
                current["epenthetic"] = True
            continue
        if label == "N":
            # Adjacent N letters are one nucleus (Figure 4 joins E and Y);
            # an N that does not follow one starts a syllable.
            joined = (i and labels[i - 1] == "N" and current is not None
                      and current["ng"] and not current["epenthetic"])
            if not joined:
                if current is None or current["ng"] or current["epenthetic"]:
                    current = fresh()
                    syllables.append(current)
            current["ng"] += word[i]
            current["np"].append(aligned[i])
            continue
        if label == "Cd" and current is not None:
            current["cg"] += word[i]
            current["cp"].append(aligned[i])
    return syllables


class Model:
    """The three distributions of Section III, counted from training pairs."""

    def __init__(self):
        self.labels = collections.defaultdict(collections.Counter)
        self.mapping = collections.defaultdict(collections.Counter)
        self.tones = collections.defaultdict(collections.Counter)

    def train(self, examples):
        for word, aligned, slots, labels, tones in examples:
            for i, label in enumerate(labels):
                window = _window(word, i)
                for form, _ in _backoffs(window, len(window) // 2):
                    self.labels[form][label] += 1

            # Eq. 8: target phoneme given the graphemes and source phones of
            # that sub-syllabic unit.
            units = units_from_labels(word, aligned, labels)
            target = slots_to_syllables(slots, tones)
            for unit, syllable in (zip(units, target)
                                   if len(units) == len(target) else ()):
                for role, graphemes, phones, token in (
                        ("O", unit["og"], unit["op"], syllable["onset"]),
                        ("N", unit["ng"], unit["np"], syllable["nucleus"]),
                        ("Cd", unit["cg"], unit["cp"], syllable["coda"])):
                    if not graphemes or not token:
                        continue
                    self.mapping[(role, graphemes, " ".join(phones))][token] += 1
                    self.mapping[(role, graphemes, "*")][token] += 1

            # Eq. 9: tone given the previous tone and the syllable's phonemes.
            previous = "#"
            for syllable in target:
                key = (previous, syllable["onset"], syllable["nucleus"],
                       syllable["coda"])
                self.tones[key][syllable["tone"]] += 1
                self.tones[("*", syllable["onset"], syllable["nucleus"],
                            syllable["coda"])][syllable["tone"]] += 1
                self.tones[("*", "*", syllable["nucleus"],
                            syllable["coda"])][syllable["tone"]] += 1
                previous = syllable["tone"]
        return self

    def label_for(self, word, i):
        window = _window(word, i)
        for form, _ in _backoffs(window, len(window) // 2):
            if form in self.labels:
                return self.labels[form].most_common(1)[0][0]
        return "N" if word[i] in VOWEL_LETTERS else "O"

    def phoneme_for(self, role, grapheme, source_phone, fallback):
        for key in ((role, grapheme, source_phone), (role, grapheme, "*")):
            if key in self.mapping:
                return self.mapping[key].most_common(1)[0][0]
        return fallback

    def tone_for(self, previous, onset, nucleus, coda):
        for key in ((previous, onset, nucleus, coda), ("*", onset, nucleus, coda),
                    ("*", "*", nucleus, coda)):
            if key in self.tones:
                return self.tones[key].most_common(1)[0][0]
        return "_1"


def slots_to_syllables(slots, tones=None):
    """Group a slot sequence back into syllables, with their tone slot.

    tones, when given, are the markers target_tones read off the same line;
    without them every syllable is ngang, which is only right for generating.
    """
    out, current = [], None
    for role, token in slots:
        if role == "O":
            current = {"onset": token, "nucleus": "", "coda": "", "tone": "_1"}
            out.append(current)
            continue
        if role == "N":
            if current is None or current["nucleus"]:
                current = {"onset": "", "nucleus": "", "coda": "", "tone": "_1"}
                out.append(current)
            current["nucleus"] = token
        elif role == "Cd" and current is not None:
            current["coda"] = token
    for syllable, tone in zip(out, tones or ()):
        syllable["tone"] = tone
    return out


def transliterate(word, aligned, model):
    """A source word and its letter-aligned phones -> their X-SAMPA reading."""
    labels = [model.label_for(word, i) for i in range(len(word))]
    syllables = units_from_labels(word, aligned, labels)
    if not syllables:
        return None

    out, previous = [], "#"
    for unit in syllables:
        onset = model.phoneme_for("O", unit["og"], " ".join(unit["op"]), "") \
            if unit["og"] else ""
        if unit["epenthetic"]:
            nucleus = EPENTHETIC
        elif unit["ng"]:
            nucleus = model.phoneme_for("N", unit["ng"], " ".join(unit["np"]), "a:")
        else:
            continue
        coda = model.phoneme_for("Cd", unit["cg"], " ".join(unit["cp"]), "") \
            if unit["cg"] else ""

        tone = model.tone_for(previous, onset, nucleus, coda)
        previous = tone
        out.append(" ".join(p for p in (onset, nucleus, coda, tone) if p))
    return " . ".join(out) if out else None


_TRAINED = None


def trained():
    """The model, fitted on every pair their data yields. Cached."""
    global _TRAINED
    if _TRAINED is None:
        _TRAINED = Model().train(training_pairs())
    return _TRAINED


def read(word, phones):
    """A word and its CMUdict phones -> quốc ngữ readings by their method."""
    line = ngo.input_line(word, phones)
    if not line:
        return []
    aligned = line.split("\t\t")[1].split()
    sampa = transliterate(word, aligned, trained())
    return sorted(ngo.readings(sampa) or []) if sampa else []
