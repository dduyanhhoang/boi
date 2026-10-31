"""How often a misspelling still reads the way the word itself does.

A reader types disneyland as dissneeland and expects đít ni len either way.
The eval cannot measure that, because every row in it is spelled correctly,
so this perturbs the gold words the way people actually mistype and asks
whether the reading survives.

    uv run scripts/check_robustness.py [--show 20]
"""
import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from boi import generate  # noqa: E402

VOWELS = set("aeiou")


def variants(word):
    """Spellings of the same word a person might plausibly type."""
    for i in range(1, len(word) - 1):
        # A doubled consonant between vowels: disney -> dissney.
        if (word[i] not in VOWELS and word[i - 1] in VOWELS
                and word[i + 1] in VOWELS and word[i] != word[i + 1]):
            yield word[:i + 1] + word[i] + word[i + 1:]
        # A doubled vowel for a long one: disney -> disneey.
        if word[i] in VOWELS and word[i - 1] not in VOWELS:
            yield word[:i + 1] + word[i] + word[i + 1:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", type=int, default=12)
    args = ap.parse_args()

    with open(ROOT / "data" / "eval_v0.csv", encoding="utf-8") as f:
        words = [r["word"] for r in csv.DictReader(f)]

    same = total = 0
    drifted = []
    for word in words:
        base = generate.candidates(word, 1)
        if not base:
            continue
        for variant in variants(word):
            total += 1
            got = generate.candidates(variant, 1)
            if got and got[0] == base[0]:
                same += 1
            else:
                drifted.append((word, base[0], variant,
                                got[0] if got else "-"))

    print(f"  {total} misspellings of {len(words)} words")
    print(f"  read the same as the word itself: {same}/{total} = {same / total:.3f}")
    if drifted:
        print(f"\n  a sample of the {len(drifted)} that drift:")
        for word, base, variant, got in drifted[:args.show]:
            print(f"    {word:14} {base:22} {variant:16} {got}")


if __name__ == "__main__":
    main()
