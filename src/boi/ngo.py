"""Decode Ngo et al.'s X-SAMPA readings into quốc ngữ.

Their data (data/ngo/) writes Vietnamese as X-SAMPA with tone numbers:
`b_< @: _3 . r\\ a:U _1` is bờ rao. This turns that into letters so the two
systems can be compared, and so the playground can show their reading beside
this one.

Where the notation cannot tell two Vietnamese spellings apart, which it
cannot for s and x, d and gi, or ch and tr, every possibility comes back and
any of them counts as a match.

It also builds the input their transliterator wants, which is one phone
symbol per letter with `_` where a letter is silent, so their system can be
run on any word rather than only the 2,400 they published.
"""

import collections
import subprocess
import sys
import tempfile

import itertools
import unicodedata
from pathlib import Path

from . import vi

DATA = Path(__file__).resolve().parents[2] / "data" / "ngo"

TONES = {"_1": "", "_2": "́", "_3": "̀",
         "_4": "̉", "_5": "̃", "_6": "̣"}

# X-SAMPA onset -> the Vietnamese spellings it could be.
ONSETS = {
    "b_<": ["b"], "d_<": ["đ"], "t": ["t"], "t_h": ["th"], "k": ["k"],
    "p": ["p"], "m": ["m"], "n": ["n"], "N": ["ng"], "J\\": ["nh"],
    "f": ["ph"], "v": ["v"], "s": ["s", "x"], "z": ["d", "gi"],
    "h": ["h"], "x": ["kh"], "G": ["g"], "l": ["l"], "r\\": ["r"],
    "ts\\": ["ch", "tr"], "w": ["g"], "j": ["d"],
}
# X-SAMPA nucleus -> Vietnamese letters.
NUCLEI = {
    "a:": "a", "a": "ă", "@:": "ơ", "@": "â", "E": "e", "e": "ê",
    "O": "o", "o": "ô", "i": "i", "u": "u", "1": "ư",
    "a:I": "ai", "aI": "ay", "@I": "ây", "a:U": "ao", "aU": "au",
    "@U": "âu", "u@": "uô", "i@": "iê", "1@": "ươ", "iU": "iu",
    "EU": "eo", "eU": "êu", "OI": "oi", "oI": "ôi", "uI": "uy",
    "ui:": "ui", "Oa:": "oa", "OE": "oe", "i@U": "iêu", "ue": "uê",
}
CODAS = {"n": "n", "t": "t", "k": "c", "p": "p", "N": "ng", "m": "m",
         "J": "nh", "c": "ch", "l": "u", "h": "", "v": ""}
# The tone mark sits on the second letter of these, on the first of the rest.
_TWO_PART = ("iê", "uô", "ươ", "iêu")


def spell_onset(onset, nucleus):
    """c/k/qu and g/gh are decided by what follows, as everywhere else."""
    if onset == "k":
        return "k" if nucleus[0] in "ieê" else "c"
    if onset == "g":
        return "gh" if nucleus[0] in "ieê" else "g"
    return onset


def decode(syllable):
    """One X-SAMPA syllable -> every quốc ngữ spelling it could be."""
    parts = syllable.split()
    if not parts:
        return []
    tone = TONES.get(parts[-1], "") if parts[-1].startswith("_") else ""
    body = [p for p in parts if not p.startswith("_")]
    if not body:
        return []

    onsets = [""]
    if body[0] in ONSETS and len(body) > 1:
        onsets = ONSETS[body[0]]
        body = body[1:]
    if not body or body[0] not in NUCLEI:
        return []
    nucleus = NUCLEI[body[0]]
    coda = "".join(CODAS.get(p, "?") for p in body[1:])
    if "?" in coda:
        return []

    # iê, uô and ươ are spelled ia, ua and ưa when nothing closes them.
    if not coda:
        nucleus = {"iê": "ia", "uô": "ua", "ươ": "ưa"}.get(nucleus, nucleus)
    i = 1 if nucleus in _TWO_PART else 0
    marked = unicodedata.normalize("NFC", nucleus[: i + 1] + tone + nucleus[i + 1:])

    out = []
    for onset in onsets:
        text = spell_onset(onset, nucleus) + marked + coda
        # Anything that will not round trip is notation this decoder does not
        # understand, so drop it rather than score against a string that is
        # not Vietnamese.
        try:
            if vi.render_word(vi.parse_word(text)) == text:
                out.append(text)
        except ValueError:
            pass
    return out


def readings(line):
    """One X-SAMPA word -> every quốc ngữ reading it could be, or None."""
    per_syllable = [decode(s) for s in line.strip().split(" . ")]
    if not all(per_syllable):
        return None
    if sum(len(s) for s in per_syllable) > 64:
        per_syllable = [s[:1] for s in per_syllable]
    return {" ".join(combo) for combo in itertools.product(*per_syllable)}


def pairs(reference=True):
    """{english word: {every quốc ngữ reading it could be}} from their data."""
    words = [l.split("\t")[0].strip()
             for l in open(DATA / "large_test.lex", encoding="utf-8")]
    name = "large_test.vie" if reference else "large_test.output"
    lines = open(DATA / name, encoding="utf-8").read().splitlines()
    out = {}
    for word, line in zip(words, lines):
        got = readings(line)
        if got:
            out[word] = got
    return out


# --- feeding their transliterator ---------------------------------------
#
# Their input is one symbol per letter in a stress-free ARPAbet with
# allophones. These are the regular substitutions, counted off their own
# aligned lexicon: AH -> AX 392 times, ER -> AXR 117, IH -> IX 92, and a
# final stop goes unreleased.
ALLOPHONES = {"AH0": "AX", "ER0": "AXR", "IH0": "IX", "IH2": "IX"}
UNRELEASED = {"T": "TD", "D": "DD", "K": "KD", "P": "PD", "B": "BD", "G": "GD"}

_LETTER_PHONE = None


def _letter_phone_counts():
    """How often each letter carries each symbol, from their aligned lexicon."""
    global _LETTER_PHONE
    if _LETTER_PHONE is None:
        counts = collections.Counter()
        for line in open(DATA / "large_test.lex", encoding="utf-8"):
            if "\t\t" not in line:
                continue
            word, phones = line.strip().split("\t\t")
            symbols = phones.split()
            if len(symbols) == len(word):
                counts.update(zip(word, symbols))
        _LETTER_PHONE = counts
    return _LETTER_PHONE


def their_phones(phones):
    """CMUdict phones -> their symbol set, stress dropped, allophones applied."""
    out = []
    for i, phone in enumerate(phones):
        if phone in ALLOPHONES:
            out.append(ALLOPHONES[phone])
            continue
        bare = phone.rstrip("012")
        # A stop at the end of a word is unreleased in their transcription.
        if i == len(phones) - 1 and bare in UNRELEASED:
            out.append(UNRELEASED[bare])
        else:
            out.append(bare)
    return out


def align_to_letters(word, phones):
    """One symbol per letter, _ where a letter is silent. None if it will not fit.

    Scored by how often their own lexicon puts that symbol on that letter.
    Reproduces their alignment on 82% of held-out words; the misses are which
    of two adjacent letters takes a phone, which does not change the syllable.
    """
    counts = _letter_phone_counts()
    n, m = len(word), len(phones)
    if m > n:
        return None
    worst = float("-inf")
    best = [[worst] * (m + 1) for _ in range(n + 1)]
    back = [[None] * (m + 1) for _ in range(n + 1)]
    best[0][0] = 0.0
    for i in range(n):
        for j in range(m + 1):
            if best[i][j] == worst:
                continue
            if best[i][j] - 0.5 > best[i + 1][j]:
                best[i + 1][j] = best[i][j] - 0.5
                back[i + 1][j] = ("_", i, j)
            if j < m:
                seen = counts.get((word[i], phones[j]), 0)
                value = best[i][j] + (1 + seen ** 0.5 if seen else -0.2)
                if value > best[i + 1][j + 1]:
                    best[i + 1][j + 1] = value
                    back[i + 1][j + 1] = (phones[j], i, j)
    if best[n][m] == worst:
        return None
    out, i, j = [], n, m
    while back[i][j]:
        symbol, i, j = back[i][j][0], back[i][j][1], back[i][j][2]
        out.append(symbol)
    return out[::-1]


def input_line(word, phones):
    """The line their transliterator reads, or None if the word will not align."""
    aligned = align_to_letters(word, their_phones(phones))
    return f"{word}\t\t{' '.join(aligned)}" if aligned else None


CODE = Path(__file__).resolve().parents[2] / "third_party" / "ngo"


def run_their_system(words, pronunciations):
    """Their transliterator over a word list -> {word: quốc ngữ readings}.

    The input is reconstructed from CMUdict, since their own lexicon covered
    words CMUdict does not. Close to what they fed it, not identical, so
    callers should keep these apart from the published readings in DATA.
    """
    lines, kept = [], []
    for word in words:
        line = input_line(word, pronunciations[word][0])
        if line:
            lines.append(line)
            kept.append(word)
    if not kept:
        return {}

    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "in.lex"
        target = Path(tmp) / "out.txt"
        source.write_text("\n".join(lines) + "\n", encoding="utf-8")
        done = subprocess.run(
            [sys.executable, "transliterator.py", str(source), str(target)],
            cwd=CODE, capture_output=True, text=True, check=False)
        if done.returncode or not target.exists():
            raise RuntimeError(done.stderr[-2000:])
        produced = target.read_text(encoding="utf-8").splitlines()

    out = {}
    for word, line in zip(kept, produced):
        decoded = readings(line)
        if decoded:
            out[word] = sorted(decoded)
    return out
