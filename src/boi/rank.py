"""Score a candidate reading. Lower is better.

The score is the sum of the mapping-table penalties that produced it, plus
the structural penalty from syllabify, plus a penalty for a syllable that is
not legal Vietnamese (a kept onset cluster such as phren). boi.md also wants a
panphon distance filter and a syllable-frequency prior; neither is here, and
the note at the bottom says what each would add.
"""

from . import vi
from .rhymes import RHYMES

_ILLEGAL_ONSET = 2.0
_UNSEEN_RHYME = 0.5


def score(syls, table_penalty, structural_penalty):
    illegal = sum(_ILLEGAL_ONSET for s in syls if s.onset in vi.CLUSTERS)
    rare = sum(_UNSEEN_RHYME for s in syls if (s.nucleus, s.coda) not in RHYMES)
    return table_penalty + structural_penalty + illegal + rare


# Not implemented for v0.0.1:
#   panphon feature distance as a filter. It needs the panphon dependency and
#   an IPA form of each candidate, and boi.md is explicit that argmax
#   similarity drifts toward transliteration, so it cannot rank on its own.
#   A corpus-counted syllable-frequency prior. rhymes.py stands in for it with
#   dev counts, which covers the rhyme side but not onset+rhyme pairs.
