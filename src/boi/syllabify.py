"""English phones -> Vietnamese syllable slots, as a few structural variants.

Each slot keeps ARPAbet phones, not Vietnamese pieces; phonemap turns them
into letters later. A word yields more than one variant where Vietnamese has
more than one repair available: a cluster can take an inserted vowel or stay
as it is, and a consonant before a final -ing or -y may geminate.
"""

from typing import NamedTuple

from .phonemap import TENSE as _TENSE

VOWELS = {
    "AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY",
    "IH", "IY", "OW", "OY", "UH", "UW",
}
# English allows these before l/r, so the pair can share one Vietnamese onset
# or split into an inserted syllable. A nasal cannot: online is "on lai".
_CLUSTER_HEADS = {"P", "B", "T", "D", "K", "G", "F", "TH", "S"}
_INSERTED_NUCLEUS = "ơ"
# English allows these to open a syllable too, and they resist splitting more
# than a C+l or C+r pair does: e-sport, not es-port.
_S_CLUSTERS = {("S", "P"), ("S", "T"), ("S", "K"), ("S", "M"), ("S", "N"),
               ("S", "L"), ("S", "W")}
# _TENSE comes from phonemap: a tense vowel or diphthong can end a syllable,
# so a cluster after it stays whole (e-sport, mi-stake, mai cờ rô), while a
# checked one takes a consonant from the run (sys-tem, up-load, óp lai).
# Before a final -ing or -y the gold geminates any of these, even voiced N
# (trên ninh), and it overwrites an r that was going to drop (pác kinh, pát ti).
_GEMINATES = {"P", "T", "K", "N"}
# Elsewhere it geminates only a voiceless consonant, between a primary
# stressed syllable and an unstressed one. Every gold doubling follows a
# primary stress; hospital's is secondary, and it is hót pi tồ, not hót pít tồ: óp phít, súp pơ, phát sừn, tích két. Not ca
# mê ra (voiced), not bờ lu tút (the next vowel is stressed), and not after
# /eɪ/ or /oʊ/, which would rather keep their offglide: sờ tây sừn, mai cờ rô.
_VOICELESS = {"P", "T", "K", "F", "S", "SH", "CH", "TH"}
_KEEPS_OFFGLIDE = {"EY", "OW"}
# A Vietnamese reader sees -tion as one piece and says sừn wherever it sits.
# CMUdict gives it away: the vowel letters are io and the onset is a sibilant.
# At the end of a word the n already closes it, but inside one the n runs off
# to the next syllable and international reads na-ti-o-nal. The n doubles
# instead, so the piece keeps its coda: in tơ nát sừn nồ.
_TION_LETTERS = "io"
_SIBILANTS = {"SH", "ZH", "CH", "S", "Z"}


class Slot(NamedTuple):
    onset: tuple = ()        # ARPAbet phones
    nucleus: str = ""        # ARPAbet vowel, or "" for an inserted syllable
    coda: tuple = ()
    stress: str = ""
    glide: bool = False      # w-glide, from W
    yod: bool = False        # i-onglide, from Y
    inserted: bool = False
    final: bool = False
    first: bool = False
    letter: str = ""        # the vowel letters this phone was written with


def _strip_stress(phones):
    out = []
    for p in phones:
        if p[-1].isdigit():
            out.append((p[:-1], p[-1]))
        else:
            out.append((p, ""))
    return out


# Runs that are a legal Vietnamese onset on their own, so they need no repair.
_VI_ONSETS = {("T", "R"), ("T", "S")}
ONSET_RUNS_KEEP = {("T", "S")}   # pizza -> pi da, never pít sa


def _is_onset_run(run):
    if len(run) == 2 and run[1] in ("L", "R") and run[0] in _CLUSTER_HEADS:
        return True
    if run in _S_CLUSTERS:
        return True
    return run in (("T", "R"), ("T", "S"))


# These nuclei always end in an offglide (lai, đao), which fills the coda slot,
# so a following consonant run has to go to the next onset: ai sờ cờ rim.
_OFFGLIDE_NUCLEI = {"AY", "AW", "OY"}


def _split_run(run, left=None):
    """Consonants between two vowels -> (coda of the left, onset of the right)."""
    if run and run[-1] == "W":
        return run[:-1], run[-1:]
    if run and run[-1] == "Y":
        coda, onset = _split_run(run[:-1], left)
        return coda, onset + ("Y",)
    if left and left[0] in _OFFGLIDE_NUCLEI:
        # The offglide fills the coda, so a consonant that was going to be the
        # coda either becomes its own syllable (ai sờ cờ rim) or drops
        # altogether (đao lốt). Only a voiceless obstruent survives.
        coda, onset = _split_run(run)
        return (), (coda if coda and coda[-1] in _VOICELESS else ()) + onset
    if run in ONSET_RUNS_KEEP:
        return (), run
    for n in range(min(2, len(run)), 0, -1):
        if n == 1 or _is_onset_run(run[-n:]):
            coda, onset = run[:-n], run[-n:]
            # A checked vowel has to close, so it takes the first consonant
            # rather than leaving a cluster to repair: ắp lốt, not ă pờ lốt.
            if (not coda and len(onset) > 1 and left
                    and left[1] in ("1", "2") and left[0] not in _TENSE):
                coda, onset = onset[:1], onset[1:]
            return coda, onset
    return run, ()


def _free_the_r(phones):
    """An unstressed ER before another vowel is a schwa plus an r onset.

    CMUdict writes camera as K AE1 M ER0 AH0, with the r inside the vowel, so
    nothing is left to open the last syllable and it comes out ca mơ a. Split
    it and the r opens the syllable it belongs to: ca mê ra.
    """
    out = []
    for i, phone in enumerate(phones):
        nxt = phones[i + 1] if i + 1 < len(phones) else ""
        # Only before a reduced vowel. A stressed one after an ER0 means a
        # compound boundary, where the r belongs to the piece before it:
        # poweroff is power plus off, not powe plus roff.
        if phone == "ER0" and nxt[:-1] in VOWELS and nxt[-1:] == "0":
            out += ["AH0", "R"]
        else:
            out.append(phone)
    return out


def _slots(phones, letters=None):
    """One flat pass: every English vowel becomes one Vietnamese syllable."""
    pairs = _strip_stress(_free_the_r(phones))
    bare = [p for p, _ in pairs]
    vowels = [i for i, p in enumerate(bare) if p in VOWELS]
    if not vowels:
        # CMUdict carries a few vowelless entries (hmm, shh) and the spelling
        # path can produce one too. Vietnamese has no vowelless syllable, so a
        # schwa carries them: the last consonant closes it, the rest open it.
        if not bare:
            return []
        onset, coda = (tuple(bare[:-1]), tuple(bare[-1:])) if len(bare) > 1 \
            else (tuple(bare), ())
        return [Slot(onset, "AH", coda, "1", final=True)]

    onsets = [tuple(bare[: vowels[0]])]
    codas = []
    for left, right in zip(vowels, vowels[1:]):
        coda, onset = _split_run(tuple(bare[left + 1 : right]),
                                 (bare[left], pairs[left][1]))
        codas.append(coda)
        onsets.append(onset)
    codas.append(tuple(bare[vowels[-1] + 1 :]))

    out = []
    for n, (i, onset, coda) in enumerate(zip(vowels, onsets, codas)):
        glide = bool(onset) and onset[-1] == "W"
        yod = bool(onset) and onset[-1] == "Y"
        if glide and len(onset) > 1:
            # k takes the glide with it and spells qu: quét, sờ que. Anything
            # else leaves the w to be the onset on its own, g, and peels off
            # what came before: sweet is sờ guýt, not suýt.
            if onset[-2] == "K":
                onset = onset[:-1]
        if yod:
            onset = onset[:-1] or ("Y",)
        out.append(Slot(onset, bare[i], coda, pairs[i][1], glide, yod,
                        final=n == len(vowels) - 1, first=n == 0,
                        letter=letters[n] if letters and n < len(letters) else ""))
    return out


def _geminate(slots):
    """Copy a syllable's onset back as the previous syllable's coda."""
    out = list(slots)
    changed = False
    for i, (left, right) in enumerate(zip(slots, slots[1:])):
        if len(right.onset) != 1 or left.nucleus in _OFFGLIDE_NUCLEI:
            continue
        phone = right.onset[0]
        # -ing doubles whatever is before it (ma két tinh), but -y only after
        # a stressed syllable: happy is háp pi, responsibility is bi li ti.
        is_ing = right.nucleus == "IH" and right.coda == ("NG",)
        is_y = right.nucleus == "IY" and not right.coda
        suffix = (right.final and right.stress in ("", "0", "2")
                  and (is_ing or (is_y and left.stress in ("1", "2"))))
        tion = (left.letter == _TION_LETTERS and left.nucleus == "AH"
                and left.stress == "0" and phone == "N"
                and left.onset and left.onset[-1] in _SIBILANTS)
        if tion and not left.coda:
            pass
        elif suffix and phone in _GEMINATES and left.coda in ((), ("R",)):
            pass
        elif (not left.coda and phone in _VOICELESS
              and not (right.letter == _TION_LETTERS and right.final)
              and not right.yod
              and left.stress == "1" and right.stress in ("", "0")
              and left.nucleus not in _KEEPS_OFFGLIDE):
            pass
        elif (phone == "NG" and not left.coda
              and left.stress == "1" and right.stress in ("", "0")):
            # The nasal stays as the coda; phonemap reads the onset copy
            # as g, so singer is sinh gờ and not si ngờ.
            pass
        else:
            continue
        # Keep a replaced r in the run: ("R", "K") still maps to c and still
        # leaves the nucleus open, which is what pác kinh and pát ti need.
        # A doubled /tʃ/ is only the stop closure, so it comes back as t:
        # teacher is tít chờ. A real final one keeps ch, as in sen guých.
        out[i] = out[i]._replace(coda=left.coda + ("T" if phone == "CH" else phone,))
        changed = True
    return out if changed else None


def _repair(slots, keep_clusters):
    """Break onset clusters, by inserted vowel or by keeping them as written."""
    out = []
    for slot in slots:
        if len(slot.onset) > 1 and slot.onset not in _VI_ONSETS:
            if keep_clusters:
                out.append(slot)
                continue
            # Peel every consonant but the last (or the last legal run) off as
            # its own syllable: sờ cờ rin, pờ rô, bờ lu.
            tail = slot.onset[-2:] if slot.onset[-2:] in _VI_ONSETS else slot.onset[-1:]
            for phone in slot.onset[: len(slot.onset) - len(tail)]:
                out.append(Slot(onset=(phone,), nucleus="", inserted=True))
            out.append(slot._replace(onset=tail))
            continue
        out.append(slot)
    return out


def variants(phones, letters=None):
    """Structural variants for one word, preferred first, with a penalty each."""
    base = _slots(phones, letters)
    if not base:
        return []
    out = []
    for gem, penalty in ((True, 0), (False, 1)):
        shapes = [base]
        if gem:
            geminated = _geminate(base)
            if geminated is None:
                continue
            shapes = [geminated]
        elif _geminate(base) is None:
            penalty = 0
        for keep, extra in ((False, 0), (True, 2)):
            repaired = _repair(shapes[0], keep)
            if keep and repaired == _repair(shapes[0], False):
                continue
            out.append((repaired, penalty + extra))
    return out
