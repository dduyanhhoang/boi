"""Find contexts where the gold is unanimous and the tables disagree with it.

The AE-before-d rule was found by listing every AE in the gold with its full
coda and seeing the split. This does that for every phone and every context
at once: align each gold reading to the slots that produced it, record what
the speaker chose, and report any context where two or more rows agree with
each other and none of them agree with us.

    uv run scripts/mine_rules.py            # nucleus choices, dev only
    uv run scripts/mine_rules.py --slot coda

Reads the dev split, never the whole of eval_v0.csv. It mined dev and test
together when first written, which leaked five test rows into rules; the
README records which.
"""
import argparse
import collections
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from boi import align, generate, g2p, phonemap, spell, syllabify, vi  # noqa: E402

SPLITS = ROOT / "data" / "splits"


def contexts(slot, syl, index, total):
    """Ways of describing where this slot sits, coarse to fine."""
    coda = "+".join(slot.coda) or "-"
    onset = slot.onset[-1] if slot.onset else "-"
    yield ("coda run", coda)
    yield ("coda ends", slot.coda[-1] if slot.coda else "-")
    yield ("coda starts", slot.coda[0] if slot.coda else "-")
    yield ("onset", onset)
    yield ("stress", slot.stress or "-")
    yield ("letter", slot.letter or "-")
    yield ("position", "final" if slot.final else ("first" if index == 0 else "mid"))
    yield ("open/closed", "closed" if slot.coda else "open")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slot", choices=["nucleus", "coda", "onset"],
                    default="nucleus")
    ap.add_argument("--min-rows", type=int, default=2)
    ap.add_argument("--split", default="dev",
                    help="dev by default; test is held out, see README")
    args = ap.parse_args()

    with open(SPLITS / f"{args.split}.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # (phone, context) -> {gold piece: [words]}, and the rows we get wrong
    seen = collections.defaultdict(lambda: collections.defaultdict(list))
    wrong = collections.defaultdict(list)
    ours = collections.defaultdict(collections.Counter)

    for row in rows:
        word = row["word"]
        phones = g2p.phones(word)
        if not phones:
            continue
        hints = spell.align_vowels(word, phones)
        variants = syllabify.variants(phones, hints)
        if not variants:
            continue
        slots = variants[0][0]
        try:
            gold = vi.parse_word(row["vi_form"])
        except ValueError:
            continue

        for si, gi in align._align(slots, gold):
            slot, syl = slots[si], gold[gi]
            if slot.inserted or not slot.nucleus:
                continue
            piece = {"nucleus": syl.nucleus, "coda": syl.coda,
                     "onset": syl.onset}[args.slot]
            predicted = generate._slot_options(slot)
            if not predicted:
                continue
            best = predicted[0][0]
            mine = {"nucleus": best.nucleus, "coda": best.coda,
                    "onset": best.onset}[args.slot]
            # Same letters, different slots is not a disagreement: guốc is
            # onset g plus nucleus uô to the parser and onset g plus a w-glide
            # plus ô to the generator, and both spell the same syllable. Such
            # a row still counts towards whether the gold is unanimous; it
            # just is not a row we get wrong.
            agrees = vi.render(best._replace(tone=syl.tone)) == vi.render(syl)
            for label, value in contexts(slot, syl, si, len(slots)):
                key = (slot.nucleus, label, value)
                seen[key][piece].append(word)
                ours[key][mine] += 1
                if mine != piece and not agrees:
                    wrong[key].append(word)

    print(f"contexts where the gold agrees with itself and not with us "
          f"({args.slot}):\n")
    found = []
    for key, choices in seen.items():
        if len(choices) != 1:
            continue
        piece, words = next(iter(choices.items()))
        missed = wrong[key]
        # The gold has to be unanimous and we have to be wrong on most of it,
        # or the context is just a label on rows we already read correctly.
        if len(words) < args.min_rows or len(missed) < args.min_rows:
            continue
        found.append((len(missed), len(words), key, piece,
                      ours[key].most_common(1)[0][0], missed))

    for missed, count, (phone, label, value), piece, mine, words in sorted(
            found, key=lambda f: -f[0]):
        print(f"  {phone:4} with {label} {value!r:12} -> {piece!r:6} "
              f"({missed} of {count} rows wrong, we usually say {mine!r})")
        print(f"       {', '.join(sorted(set(words))[:8])}")
    if not found:
        print("  none")


if __name__ == "__main__":
    main()
