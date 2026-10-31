"""Tone per syllable, from English stress and the shape of the Vietnamese one.

Hand rules, in the order they are tried. docs/brief.md also proposes "unstressed
syllable before the stressed one -> huyền"; the dev rows say otherwise (sô lu
sừn, hê lô, ba na na, con tờ rôn and i ven are all ngang against report and
design), so that rule is not here. See the comment on _before_stress.
"""

_STOP_CODAS = {"p", "t", "c", "ch"}
_SIBILANTS = {"SH", "ZH", "CH"}
# Word-final -rt and -ge come out glottalised: rì pọt, sờ pọt, i mịt, mét sịt.
_NANG_CODAS = {("R", "T"), ("JH",)}
_HUYEN_BEFORE_ER = {"D", "CH"}


def tone_of(slot, syl):
    """slot is a syllabify.Slot, syl the vi.Syl built from it (tone ignored)."""
    if slot.inserted:
        return "huyen"                      # sờ, cờ, bờ, pờ
    # -tion takes huyền wherever it sits, not only at the end of a word:
    # in phô mây sừn, and in tơ nát sừn nồ.
    if (slot.nucleus == "AH" and slot.stress == "0" and slot.coda == ("N",)
            and slot.onset and slot.onset[-1] in _SIBILANTS
            and (slot.final or slot.letter == "io")):
        return "huyen"
    if slot.final:
        if slot.nucleus == "AH" and slot.stress == "0":
            if slot.coda == ("L",):
                return "huyen"              # -le/-al: gu gồ, mo đồ, le vồ
        # docs/brief.md reads a final -er as huyền with lexical exceptions.
        # The gold splits five ngang against four huyền with nothing
        # separating them, so this is observation rather than derivation:
        # these are the onsets seen to take huyền, in phâu đờ, o đờ and
        # tít chờ. Everything else is ngang.
        if slot.nucleus == "ER" and slot.stress == "0" \
                and slot.onset and slot.onset[-1] in _HUYEN_BEFORE_ER:
            return "huyen"
    if syl.coda in _STOP_CODAS:
        if slot.final and slot.coda in _NANG_CODAS:
            return "nang"                   # rì pọt, i mịt
        return "sac"                        # con tếch, láp tốp, nét
    return "ngang"


# Kept for the record: docs/brief.md's pre-stress rule fits report (rì pọt) and
# design (đì dai) and contradicts five other dev rows, so it stays off.
def _before_stress(slots, i):
    return i + 1 < len(slots) and slots[i + 1].stress == "1" and slots[i].stress == "0"
