"""End to end: English word -> ranked Vietnamese readings."""

import argparse
import itertools
import sys

from . import g2p, lexicon, phonemap, rank, syllabify, tone, vi

BUDGET = 3.0        # how far above the best table penalty to keep exploring
PER_SLOT = 4        # options kept per syllable


# A /ju/ keeps its i only word-initially (diu túp) or after a labial (com piu
# tơ). Elsewhere the gold drops it: me nu, diu túp.
_KEEPS_YOD = {"P", "B", "M", "F", "V", "Y"}


def _nucleus_options(slot):
    if slot.yod and (not slot.onset or slot.onset[-1] in _KEEPS_YOD):
        return [("i", "u", 0)] if slot.nucleus == "UW" else [("i", "", 0)]
    # R is never a Vietnamese coda, so it leaves the nucleus open as far as the
    # vowel choice goes: hardware is hát, not hót.
    closed = bool(slot.coda) and slot.coda[0] != "R"
    return phonemap.nucleus_options(slot.nucleus, slot.stress, closed, slot.coda,
                                    final=slot.final, glide=slot.glide,
                                    onset=slot.onset)


def _slot_options(slot):
    """Every (vi.Syl, penalty) this slot can become, best first."""
    if slot.inserted:
        onsets = phonemap.onset_options(slot.onset)
        return [(vi.Syl(o, "", "ơ", "", "ngang"), p) for o, p in onsets][:PER_SLOT]

    out, illegal = {}, {}
    for onset, p_on in phonemap.onset_options(slot.onset):
        for nucleus, offglide, p_nu in _nucleus_options(slot):
            if offglide:
                # Two codas are illegal, so the English coda goes.
                codas = [(offglide, 1 if slot.coda else 0)]
            else:
                codas = phonemap.coda_options(
                    slot.coda, nucleus,
                    schwa=slot.nucleus == "AH" and slot.stress == "0")
            for coda, p_co in codas:
                # Standard quốc ngữ: gh before a front vowel, but a w-glide
                # puts an o or u in between, so g stays g (sóp goe).
                spelled = ("gh" if onset == "g" and not slot.glide
                           and nucleus[0] in "ieê" else onset)
                # gi before an i nucleus would spell gii, giin, giíp. Northern
                # d, gi and r are all /z/, so the i-nucleus forms take d.
                if spelled == "gi" and nucleus[0] == "i":
                    spelled = "d"
                syl = vi.Syl(spelled, "w" if slot.glide else "", nucleus, coda, "ngang")
                penalty = p_on + p_nu + p_co
                # Vietnamese cannot say an illegal rhyme, so it is filtered.
                # Keeping the illegal ones aside means a gap in the table costs
                # accuracy on one word instead of producing no reading at all.
                target = out if vi.is_legal(syl) else illegal
                if syl not in target or penalty < target[syl]:
                    target[syl] = penalty
    best = sorted((out or illegal).items(), key=lambda kv: kv[1])
    return best[:PER_SLOT]


def candidates(word, limit=5):
    """Ranked readings for one word. Empty list if the word has no phones."""
    fixed = lexicon.LEXICON.get(word.lower())
    phones = g2p.phones(word)
    if phones is None:
        return [fixed] if fixed else []

    scored = {}
    for slots, structural in syllabify.variants(phones):
        options = [_slot_options(s) for s in slots]
        if not all(options):
            continue
        floor = sum(opts[0][1] for opts in options)
        for combo in itertools.product(*options):
            table_penalty = sum(p for _, p in combo)
            if table_penalty > floor + BUDGET:
                continue
            syls = [s._replace(tone=tone.tone_of(slot, s))
                    for slot, (s, _) in zip(slots, combo)]
            text = vi.render_word(syls)
            total = rank.score(syls, table_penalty, structural)
            if text not in scored or total < scored[text]:
                scored[text] = total

    ranked = [t for t, _ in sorted(scored.items(), key=lambda kv: (kv[1], kv[0]))]
    if fixed:
        ranked = [fixed] + [t for t in ranked if t != fixed]
    return ranked[:limit]


def read(word):
    """The single best reading, or None."""
    best = candidates(word, limit=1)
    return best[0] if best else None


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="boi", description="Read English words the way Vietnamese speakers do.")
    ap.add_argument("words", nargs="+")
    ap.add_argument("-a", "--all", action="store_true", help="show ranked alternatives")
    args = ap.parse_args(argv)

    status = 0
    for word in args.words:
        ranked = candidates(word, limit=5 if args.all else 1)
        if not ranked:
            print(f"{word}\t?  (not in CMUdict; install the oov extra for g2p_en)",
                  file=sys.stderr)
            status = 1
        elif args.all:
            print(f"{word}\t" + "  |  ".join(ranked))
        else:
            print(f"{word}\t{ranked[0]}")
    return status


if __name__ == "__main__":
    sys.exit(main())
