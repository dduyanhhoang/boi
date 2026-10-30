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


def _compound(word):
    """Phones for a split, with only the first piece keeping primary stress."""
    pieces = _split(word)
    if not pieces:
        return None
    out = []
    for n, piece in enumerate(pieces):
        for phone in _DICT[piece][0]:
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


def phones(word, predict=True):
    """Phones for any word. None only when there are no letters to read."""
    w = word.lower()
    if w in _DICT:
        return _DICT[w][0]
    if w in COMPOUNDS:
        return COMPOUNDS[w].split()
    if not predict:
        return None
    return _compound(w) or _predicted(w) or spell.phones(w)


def source(word):
    """Which of the three sources answers for this word."""
    w = word.lower()
    if w in _DICT:
        return "cmudict"
    if w in COMPOUNDS:
        return "compound"
    if _split(w):
        return "compound"
    if _predicted(w):
        return "g2p_en"
    return "spelling"
