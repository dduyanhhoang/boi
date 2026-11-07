"""End to end: English word -> ranked Vietnamese readings."""

import argparse
import itertools
import sys

from . import g2p, letters, lexicon, phonemap, rank, spell, syllabify, tone, vi

BUDGET = 3.0        # how far above the best table penalty to keep exploring
PER_SLOT = 4        # options kept per syllable


# A /ju/ keeps its i only word-initially (diu túp) or after a labial (com piu
# tơ). Elsewhere the gold drops it: me nu, diu túp.
_KEEPS_YOD = {"P", "B", "M", "F", "V", "Y"}


def _hiatus_yod(slot):
    return slot.yod and slot.onset == ("Y",) and slot.nucleus == "UW" and not slot.first


def _nucleus_options(slot):
    if slot.yod and (not slot.onset or slot.onset[-1] in _KEEPS_YOD):
        return [("i", "u", 0)] if slot.nucleus == "UW" else [("i", "", 0)]
    # R is never a Vietnamese coda, so it leaves the nucleus open as far as the
    # vowel choice goes: hardware is hát, not hót.
    closed = bool(slot.coda) and slot.coda[0] != "R"
    return phonemap.nucleus_options(slot.nucleus, slot.stress, closed, slot.coda,
                                    final=slot.final, glide=slot.glide,
                                    onset=slot.onset, letter=slot.letter,
                                    first=slot.first,
                                    after_stress=slot.after_stress,
                                    next_onset=slot.next_onset)


def _slot_options(slot):
    """Every (vi.Syl, penalty) this slot can become, best first."""
    if slot.inserted:
        onsets = phonemap.onset_options(slot.onset)
        return [(vi.Syl(o, "", syllabify._INSERTED_NUCLEUS, "", "ngang"), p)
                for o, p in onsets][:PER_SLOT]

    out, illegal = {}, {}
    onsets = phonemap.onset_options(slot.onset, slot.onset_doubled,
                                    slot.nucleus, slot.stress)
    # A /ju/ between vowels loses its /j/: reuse is rì iu, not ri diu. Only
    # word-initially is it d, as in diu túp.
    if _hiatus_yod(slot):
        onsets = [("", 0)]
    for onset, p_on in onsets:
        for nucleus, offglide, p_nu in _nucleus_options(slot):
            if offglide:
                # Two codas are illegal, so the English coda goes.
                codas = [(offglide, 1 if slot.coda else 0)]
            else:
                codas = phonemap.coda_options(
                    slot.coda, nucleus,
                    schwa=slot.nucleus == "AH" and slot.stress == "0",
                    vowel=slot.nucleus, doubled=slot.doubled,
                    reduced=slot.stress == "0")
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


def _acronym(word):
    """The reading of a word written with capitals, or None if it is not one."""
    parts = letters.acronym_parts(word, g2p.ordinary_word)
    if not parts:
        return None
    spoken = [read(text) if kind == "read" else text for kind, text in parts]
    return " ".join(spoken) if all(spoken) else None


def _hints(word, phones):
    """Which letters each vowel phone came from.

    A word built from pieces lines up piece by piece: across the whole of
    pneumonoultra the spelling sees one vowel in oul where the phones have
    two, and every letter after it would be one vowel out.
    """
    pieces = g2p.parts(word)
    if pieces:
        groups = [spell.align_vowels(text, said) for text, said in pieces]
        if all(g is not None for g in groups):
            return [letter for g in groups for letter in g]
    return spell.align_vowels(g2p.undoubled(word.lower()) or word, phones)


def candidates(word, limit=5):
    """Ranked readings for one word. Empty list if the word has no phones."""
    # A memorised reading is about the word, not its spelling, so a doubled
    # letter should not lose it: scheedule is sờ ke đùa too.
    fixed = (lexicon.LEXICON.get(word.lower())
             or lexicon.LEXICON.get(g2p.undoubled(word.lower()) or "")
             or _acronym(word))
    phones = g2p.phones(word)
    if phones is None:
        return [fixed] if fixed else []

    # The letters have to be the ones the phones came from, or the two
    # disagree: commeent takes comment's phones and must take its letters
    # too, or the ee is read as a vowel of its own.
    hints = _hints(word, phones)
    scored = {}
    for slots, structural in syllabify.variants(phones, hints):
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
    ap.add_argument("-r", "--read", action="store_true",
                    help="read the letters as Vietnamese instead of the sound")
    args = ap.parse_args(argv)

    status = 0
    for word in args.words:
        if args.read:
            reading = letters.read(word)
            if reading:
                print(f"{word}\t{reading}")
            else:
                print(f"{word}\tno letters to read", file=sys.stderr)
                status = 1
            continue

        ranked = candidates(word, limit=5 if args.all else 1)
        if not ranked:
            print(f"{word}\tno reading", file=sys.stderr)
            status = 1
        elif args.all:
            print(f"{word}\t" + "  |  ".join(ranked))
            print(f"{'':{len(word)}}\tas letters: {letters.read(word)}")
        else:
            print(f"{word}\t{ranked[0]}")
    return status


if __name__ == "__main__":
    sys.exit(main())
