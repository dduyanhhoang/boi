"""Words whose reading no rule predicts.

docs/brief.md calls these out: s/sh becomes x in some short words (xóp, xót) and not
in others (sóp pinh, phát sừn), and mall is the one final l that drops instead
of gliding. The generator produces the rule-based form for all of them; these
entries override it and the rule-based form stays available as an alternative.

Keep this list short. An entry here is an admission that a rule is missing, so
anything that turns out to generalise belongs in phonemap or tone instead.
Every entry is checked for legal syllables by tests/test_pipeline.py.
"""

LEXICON = {
    "shop": "xóp",      # s -> x, against sóp pinh
    "sauce": "xót",     # s -> x, against sót
    "mall": "mô",       # final l drops; sale glides to sêu, school takes n
    "bus": "bớt",       # /ʌ/ -> ơ, against bắc and ắp
    "schedule": "sờ ke đùa",  # JH -> đ and UH0 + L -> ua, neither seen elsewhere
    "handsome": "hen săm",    # AE + n is a elsewhere (phan, pờ lan), AH0 + m is o
    # The country's own name, so it is read as Vietnamese rather than
    # transliterated: no rule gets iê out of IY0 EH2, or mít out of -mese.
    "vietnamese": "việt nam mít",
    # Nothing predicts the x: shop is xóp where shopping is sóp, the same
    # onset and nucleus in the same morpheme. The ừm is a rule.
    "system": "xít từm",
    "taxi": "tắc xi",         # AE + k is a in action, bách, nách, lách; s is x in 3 of 37
}
