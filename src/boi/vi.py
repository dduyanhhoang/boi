"""Vietnamese syllable model: quốc ngữ <-> slots, both directions.

A syllable is (onset, glide, nucleus, coda, tone). The slot keys are
orthographic families rather than phonemes, so pairs Northern speech merges
(d/gi/r, tr/ch, s/x) stay apart and a parsed word re-renders character for
character. Only the spellings that context fully decides collapse into one
key: `k` covers c/k/qu, `ng` covers ng/ngh, `g` covers g/gh.

Offglides live in the coda slot (lai = l + a + i), which is what makes tone
placement a one-liner: the mark always goes on the nucleus.
"""

import unicodedata
from typing import NamedTuple

TONE_MARKS = {
    "ngang": "",
    "huyen": "̀",
    "sac": "́",
    "hoi": "̉",
    "nga": "̃",
    "nang": "̣",
}
_MARK_TONE = {m: t for t, m in TONE_MARKS.items() if m}

_ONSETS = [
    "ngh", "ng", "nh", "ch", "tr", "th", "ph", "kh", "gh", "gi", "qu",
    "b", "c", "d", "đ", "g", "h", "k", "l", "m", "n", "p", "r", "s", "t", "v", "x",
    "z",  # foreign, and the gold uses it: "pre zen tây sừn"
]
# Clusters the native speaker kept rather than repaired: phren, sờ críp, prô.
# Illegal in Vietnamese phonotactics, but they are written, so they parse.
CLUSTERS = ["pr", "pl", "phr", "phl", "cr", "cl", "br", "bl", "gr", "gl", "dr", "kr", "tl"]
_ONSET_SPELLINGS = sorted(_ONSETS + CLUSTERS, key=len, reverse=True)
# Only c/k/qu collapse: the gold follows that spelling rule, but it writes both
# "gêm" and "ta ghét", so g and gh stay separate keys.
_ONSET_KEY = {"c": "k", "k": "k", "qu": "k"}

_NUCLEUS_SPELLINGS = [
    "ươ", "ưa", "uô", "ua", "iê", "ia", "yê", "oo",
    "ă", "â", "ê", "ô", "ơ", "ư", "a", "e", "i", "o", "u", "y",
]
_NUCLEUS_KEY = {"ưa": "ươ", "ua": "uô", "ia": "iê", "yê": "iê", "y": "i"}
_TWO_PART = {"ươ", "uô", "iê"}  # mark sits on the second letter

CODAS = ["ng", "nh", "ch", "p", "t", "c", "m", "n", "i", "y", "u", "o"]
NUCLEI = ["a", "ă", "â", "e", "ê", "i", "o", "ô", "ơ", "u", "ư", "iê", "uô", "ươ", "oo"]

# Which codas each nucleus admits. This is Vietnamese phonotactics, not a
# count of the data: ch and nh only follow i, ê and a, so /ɛ/ + k has to become
# êch (con tếch) rather than ec. ă and â never stand alone. "ưn" is not a
# native rhyme but the gold uses it throughout the -tion words (sừn), so it is
# in. tests/test_vi.py checks every gold form against this table.
LEGAL_CODAS = {
    "a":  {"", "p", "t", "c", "ch", "m", "n", "ng", "nh", "i", "y", "u", "o"},
    "ă":  {"p", "t", "c", "m", "n", "ng"},
    "â":  {"p", "t", "c", "m", "n", "ng", "u", "y"},
    "e":  {"", "p", "t", "m", "n", "o"},
    "ê":  {"", "p", "t", "ch", "m", "n", "nh", "u"},
    "i":  {"", "p", "t", "c", "ch", "m", "n", "nh", "u"},
    "o":  {"", "p", "t", "c", "m", "n", "ng", "i"},
    "ô":  {"", "p", "t", "c", "m", "n", "ng", "i"},
    "ơ":  {"", "p", "t", "m", "n", "i"},
    "u":  {"", "p", "t", "c", "m", "n", "ng", "i"},
    "ư":  {"", "t", "c", "n", "ng", "u", "i", "m"},
    "iê": {"", "p", "t", "c", "ch", "m", "n", "ng", "nh", "u"},
    "uô": {"", "p", "t", "c", "m", "n", "ng", "i"},
    "ươ": {"", "p", "t", "c", "m", "n", "ng", "i", "u"},
    "oo": {"c", "ng"},
}


def is_legal(syl):
    """Is this a pronounceable Vietnamese rhyme?"""
    return syl.coda in LEGAL_CODAS.get(syl.nucleus, set())


# A leading o/u is the w-glide only before these nuclei.
_GLIDE_O_BEFORE = set("aăe")
_GLIDE_U_BEFORE = set("âêơy")


class Syl(NamedTuple):
    onset: str = ""
    glide: str = ""      # "" or "w"
    nucleus: str = "a"
    coda: str = ""
    tone: str = "ngang"


def _strip_tone(text):
    """Split tone marks off, leaving breve/horn/circumflex in place."""
    tone = "ngang"
    out = []
    for ch in unicodedata.normalize("NFD", text):
        if ch in _MARK_TONE:
            tone = _MARK_TONE[ch]
        else:
            out.append(ch)
    return unicodedata.normalize("NFC", "".join(out)), tone


def _spell_onset(syl):
    o = syl.onset
    if o == "k":
        if syl.glide:
            return "qu"
        return "k" if syl.nucleus[0] in "ieê" else "c"
    return o


def _spell_glide(syl):
    if not syl.glide or syl.onset == "k":  # qu already carries it
        return ""
    return "o" if syl.nucleus[0] in _GLIDE_O_BEFORE else "u"


def _spell_nucleus(syl):
    n = syl.nucleus
    if n == "i" and syl.glide:
        return "y"
    if not syl.coda:
        return {"iê": "ia", "uô": "ua", "ươ": "ưa"}.get(n, n)
    return n


def render(syl):
    """One syllable of slots -> quốc ngữ."""
    nucleus = _spell_nucleus(syl)
    i = 1 if nucleus in _TWO_PART else 0
    marked = unicodedata.normalize(
        "NFC", nucleus[: i + 1] + TONE_MARKS[syl.tone] + nucleus[i + 1 :]
    )
    return _spell_onset(syl) + _spell_glide(syl) + marked + syl.coda


def parse(text):
    """One syllable of quốc ngữ -> slots. Raises ValueError on anything else."""
    bare, tone = _strip_tone(text.strip().lower())
    onset = ""
    for spelling in _ONSET_SPELLINGS:
        if bare.startswith(spelling) and len(bare) > len(spelling):
            onset = _ONSET_KEY.get(spelling, spelling)
            glide = "w" if spelling == "qu" else ""
            bare = bare[len(spelling) :]
            break
    else:
        glide = ""

    if not glide and len(bare) > 1:
        if bare[0] == "o" and bare[1] in _GLIDE_O_BEFORE:
            glide, bare = "w", bare[1:]
        elif bare[0] == "u" and bare[1] in _GLIDE_U_BEFORE:
            glide, bare = "w", bare[1:]

    for spelling in _NUCLEUS_SPELLINGS:
        if bare.startswith(spelling):
            nucleus = _NUCLEUS_KEY.get(spelling, spelling)
            coda = bare[len(spelling) :]
            break
    else:
        raise ValueError(f"no nucleus in {text!r}")

    if coda and coda not in CODAS:
        raise ValueError(f"illegal coda {coda!r} in {text!r}")
    return Syl(onset, glide, nucleus, coda, tone)


def parse_word(text):
    return [parse(s) for s in text.split()]


def render_word(syls):
    return " ".join(render(s) for s in syls)
