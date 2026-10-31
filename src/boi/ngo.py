"""Decode Ngo et al.'s X-SAMPA readings into quốc ngữ.

Their data (data/ngo/) writes Vietnamese as X-SAMPA with tone numbers:
`b_< @: _3 . r\\ a:U _1` is bờ rao. This turns that into letters so the two
systems can be compared, and so the playground can show their reading beside
this one.

Where the notation cannot tell two Vietnamese spellings apart, which it
cannot for s and x, d and gi, or ch and tr, every possibility comes back and
any of them counts as a match.
"""

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
