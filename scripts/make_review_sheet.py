"""Run the generator over a word list and emit a sheet for a native speaker.

Step 9 of docs/brief.md: the generator proposes, a speaker corrects, the corrected
rows join data/eval_v0.csv and the tables get refitted. Columns match the eval
set so a reviewed sheet can be concatenated straight on.

    uv run scripts/make_review_sheet.py words.txt > sheet.csv
    printf 'router\\nbrunch\\n' | uv run scripts/make_review_sheet.py -

vi_form holds the generator's first choice, alt_forms the rest of its top five.
The reviewer edits vi_form and sets status to approved or corrected.
"""
import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from boi import g2p, generate  # noqa: E402

FIELDS = ["id", "word", "arpabet", "vi_form", "alt_forms", "vi_native", "tags",
          "confidence", "status"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("words", help="file with one word per line, or - for stdin")
    args = ap.parse_args()

    stream = sys.stdin if args.words == "-" else open(args.words, encoding="utf-8")
    with stream:
        words = [w.strip().lower() for w in stream if w.strip()]

    writer = csv.DictWriter(sys.stdout, fieldnames=FIELDS)
    writer.writeheader()
    for i, word in enumerate(dict.fromkeys(words), 1):
        phones = g2p.phones(word)
        ranked = generate.candidates(word, limit=5)
        writer.writerow({
            "id": f"g{i:04d}",
            "word": word,
            "arpabet": " ".join(phones) if phones else "",
            "vi_form": ranked[0] if ranked else "",
            "alt_forms": ";".join(ranked[1:]),
            "vi_native": "",
            "tags": "",
            "confidence": "",
            "status": "generated",
        })


if __name__ == "__main__":
    main()
