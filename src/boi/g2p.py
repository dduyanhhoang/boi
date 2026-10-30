"""English word -> ARPAbet phones with stress digits.

CMUdict first. For a word CMUdict does not have, g2p_en predicts the phones,
which boi.md allows only as this fallback. g2p_en is an optional dependency
(`uv sync --extra oov`) because it pulls in numpy and nltk and downloads a
tagger on first use; without it, an unknown word returns None.
"""

import cmudict

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
    """First CMUdict pronunciation, else a predicted one, else None."""
    w = word.lower()
    if w in _DICT:
        return _DICT[w][0]
    if w in COMPOUNDS:
        return COMPOUNDS[w].split()
    return _predicted(w) if predict else None
