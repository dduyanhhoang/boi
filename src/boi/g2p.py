"""English word -> ARPAbet phones with stress digits.

Three sources, in order of how much they can be trusted:

1. CMUdict, plus the handful of compounds it lacks.
2. g2p_en, if it is installed (`uv sync --extra oov`). docs/brief.md allows it
   only as this fallback; it pulls in numpy and nltk and downloads a tagger on
   first use, so it stays optional.
3. spell.py, which reads the letters. Always available, least accurate, and
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
    return _predicted(w) or spell.phones(w)


def source(word):
    """Which of the three sources answers for this word."""
    w = word.lower()
    if w in _DICT:
        return "cmudict"
    if w in COMPOUNDS:
        return "compound"
    if _predicted(w):
        return "g2p_en"
    return "spelling"
