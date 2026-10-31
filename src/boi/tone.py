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
_NGANG_BEFORE_ER = {"T", "V", "G", "P", "K"}


def tone_of(slot, syl):
    """slot is a syllabify.Slot, syl the vi.Syl built from it (tone ignored)."""
    if slot.inserted:
        return "huyen"                      # sờ, cờ, bờ, pờ
    # A reduced ừn takes huyền wherever it sits: in phô mây sừn and in tơ
    # nát sừn nồ for -tion, im pờ rúp mừn for a -ment after a stressed
    # syllable. The ư is what carries it, so the onset does not matter.
    if (slot.nucleus == "AH" and slot.stress == "0" and slot.coda[:1] == ("N",)
            and syl.nucleus == "ư"
            and (slot.final or slot.letter == "io")):
        return "huyen"
    if slot.final:
        if slot.stress == "0" and slot.coda == ("L",) \
                and slot.nucleus in ("AH", "UH", "UW"):
            return "huyen"                  # -le/-al/-ule: gu gồ, mo đồ, đùa
        if slot.nucleus == "AH" and slot.stress == "0":
            # The huyền goes with the ư, not with the m: dừm and từm take it,
            # ao bum does not.
            if slot.coda == ("M",) and syl.nucleus == "ư":
                return "huyen"
        # A final -er is mostly ờ and sometimes ơ. Across the eleven words
        # read so far the consonant before it partitions them without a
        # single conflict, so that is what this is: a list of the consonants
        # observed to take ngang, not a feature of them. t, v, g, p and k
        # give com piu tơ, sơ vơ, bơ gơ, súp pơ and sờ pích cơ; d, gi, ng,
        # ch and nothing at all give phâu đờ, ma na giờ, sinh gờ, tít chờ,
        # o đờ and pờ lây ờ. Voicing is not it: t and d split but g does not
        # go with d.
        if slot.nucleus == "ER" and slot.stress == "0":
            before = slot.onset[-1] if slot.onset else ""
            return "ngang" if before in _NGANG_BEFORE_ER else "huyen"
    if syl.coda in _STOP_CODAS:
        # -ious is glottalised like the other final fricatives: con sợt.
        if slot.final and (slot.coda in _NANG_CODAS or slot.letter == "iou"):
            return "nang"                   # rì pọt, i mịt, con sợt
        return "sac"                        # con tếch, láp tốp, nét
    return "ngang"


# Kept for the record: docs/brief.md's pre-stress rule fits report (rì pọt) and
# design (đì dai) and contradicts five other dev rows, so it stays off.
def _before_stress(slots, i):
    return i + 1 < len(slots) and slots[i + 1].stress == "1" and slots[i].stress == "0"
