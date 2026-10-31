"""English word -> ARPAbet phones with stress digits.

Three sources, in order of how much they can be trusted:

1. CMUdict, plus the handful of compounds it lacks.
2. A split into CMUdict words, for the compounds nobody lists: poweroff is
   power plus off, grabfood is grab plus food. Real phones, so this beats
   reading the letters whenever it finds a split.
3. g2p_en, if it is installed (`uv sync --extra oov`). docs/brief.md allows it
   only as this fallback; it pulls in numpy and nltk and downloads a tagger on
   first use, so it stays optional.
4. spell.py, which reads the letters. Always available, least accurate, and
   the reason no word comes back empty.
"""

import re

import cmudict

from . import spell

_DICT = cmudict.dict()
_G2P = None

# Words CMUdict lacks, hand-composed from the parts it does have.
COMPOUNDS = {
    "livestream": "L AY1 V S T R IY1 M",  # "live" as in /laɪv/, not /lɪv/
    "icecream": "AY1 S K R IY1 M",
    "tiktok": "T IH1 K T AA2 K",
}


# A piece shorter than this makes for junk splits: shopee is not shop plus ee.
_MIN_PIECE = 3


def _split(word, _cache={}):
    """Fewest, longest CMUdict words this word is made of, or None."""
    if word in _cache:
        return _cache[word]

    def go(i, depth):
        if i == len(word):
            return []
        if depth > 3:
            return None
        best = None
        for j in range(len(word), i + _MIN_PIECE - 1, -1):
            if word[i:j] in _DICT:
                rest = go(j, depth + 1)
                if rest is not None and (best is None or len(rest) + 1 < len(best)):
                    best = [word[i:j]] + rest
        return best

    pieces = go(0, 1)
    _cache[word] = pieces if pieces and len(pieces) > 1 else None
    return _cache[word]


def citation_table():
    """The nine CMUdict words whose citation form is not the one it lists first.

    Small enough to ship to the browser whole, which is why the shards carry
    one pronunciation per word and this sits beside them.
    """
    return {word: _citation(word) for word in _DICT
            if _citation(word) != _DICT[word][0]}


def _citation(piece):
    """The pronunciation a piece has when said alone.

    CMUdict lists the reduced form of a function word first, so and is
    AH0 N D before AE1 N D. A compound is a sequence of words said one after
    another, not a sentence, so each piece takes the stressed form it would
    have on its own: dissneeland ends in len, not lon.
    """
    entries = _DICT[piece]
    for entry in entries:
        if any(phone.endswith("1") for phone in entry):
            return entry
    return entries[0]


def _compound(word):
    """Phones for a split, with only the first piece keeping primary stress."""
    pieces = _split(word)
    if not pieces:
        return None
    out = []
    for n, piece in enumerate(pieces):
        for phone in _citation(piece):
            out.append(phone.replace("1", "2") if n and phone.endswith("1") else phone)
    return out


def _predicted(word):
    global _G2P
    if _G2P is None:
        try:
            from g2p_en import G2p
        except ImportError:
            return None
        _G2P = G2p()
    # g2p_en emits punctuation and spaces alongside phones; keep the phones.
    return [p for p in _G2P(word) if p[0].isalpha()] or None


def undoubled(word):
    """The word with each doubled letter collapsed, if that is a known word.

    A doubled letter is one sound, and doubling one is the commonest way a
    word gets misspelt: informattion, scheedule, dissney. Without this they
    fall past CMUdict to the spelling reader, which answers so differently
    that one stray letter changes the whole reading.
    """
    if word in _DICT:
        return None             # mousse is a word, not a misspelt mouse
    runs = [m.start() for m in re.finditer(r"(.)\1", word)]
    if not runs:
        return None
    # One run at a time first: offliine is offline, not ofline, and only the
    # doubled i was the mistake.
    for i in runs:
        candidate = word[:i] + word[i + 1:]
        if candidate in _DICT:
            return candidate
    collapsed = re.sub(r"(.)\1+", r"\1", word)
    return collapsed if collapsed != word and collapsed in _DICT else None


# The vowel each letter has when the letter is named: a is EY, i is AY. A
# reader who does not know the word says the letters, which is how finance
# becomes phai nan rather than phi nan.
_LETTER_NAME_VOWEL = {"a": "EY", "e": "IY", "i": "AY", "o": "OW", "u": "UW"}
_REDUCED = {"AH0", "IH0"}


def _spelled_out(word, entries):
    """A variant whose first vowel is the one its letter is named with.

    CMUdict lists finance reduced-first, as F AH0 N AE1 N S, because that is
    how it is said in running speech. The first vowel of the first syllable
    is the one a Vietnamese reader takes from the spelling, so where CMUdict
    offers a reading that agrees with the letter, that is the one to use.
    """
    first = next((p for p in entries[0] if p[-1].isdigit()), None)
    if first not in _REDUCED:
        return None
    groups = spell.align_vowels(word, entries[0])
    if not groups:
        return None
    wanted = _LETTER_NAME_VOWEL.get(groups[0])
    if not wanted:
        return None
    for entry in entries[1:]:
        vowel = next((p for p in entry if p[-1].isdigit()), None)
        if vowel and vowel[:-1] == wanted:
            return entry
    return None


def phones(word, predict=True):
    """Phones for any word. None only when there are no letters to read."""
    w = word.lower()
    if w in _DICT:
        return _spelled_out(w, _DICT[w]) or _DICT[w][0]
    if w in COMPOUNDS:
        return COMPOUNDS[w].split()
    if not predict:
        return None
    plain = undoubled(w)
    if plain:
        return _DICT[plain][0]
    return _compound(w) or _predicted(w) or spell.phones(w)


def source(word):
    """Which of the three sources answers for this word."""
    w = word.lower()
    if w in _DICT:
        return "cmudict"
    if w in COMPOUNDS:
        return "compound"
    if undoubled(w):
        return "cmudict"
    if _split(w):
        return "compound"
    if _predicted(w):
        return "g2p_en"
    return "spelling"
