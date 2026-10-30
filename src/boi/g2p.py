"""English word -> ARPAbet phones with stress digits (CMUdict)."""

import cmudict

_DICT = cmudict.dict()

# Words CMUdict lacks, hand-composed from the parts it does have.
COMPOUNDS = {
    "livestream": "L AY1 V S T R IY1 M",  # "live" as in /laɪv/, not /lɪv/
    "icecream": "AY1 S K R IY1 M",
    "tiktok": "T IH1 K T AA2 K",
}


def phones(word: str) -> list[str] | None:
    """First CMUdict pronunciation, or None when the word is unknown.

    g2p_en fallback goes here once step 8 needs it.
    """
    w = word.lower()
    if w in _DICT:
        return _DICT[w][0]
    if w in COMPOUNDS:
        return COMPOUNDS[w].split()
    return None
