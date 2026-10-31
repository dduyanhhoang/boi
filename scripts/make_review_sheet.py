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
from boi import g2p, generate, letters  # noqa: E402

FIELDS = ["id", "word", "arpabet", "vi_form", "alt_forms", "vi_native", "tags",
          "confidence", "status"]

# Patterns worth measuring separately once the rows come back. Checked against
# the spelling, so a reviewed sheet can be scored by tag like the first set.
SPELLING_TAGS = [
    ("tion", ("tion", "sion")), ("ment", ("ment",)), ("ity", ("ity",)),
    ("able", ("able", "ible")), ("ical", ("ical", "ic")),
    ("ology", ("ology", "ography")), ("agent_er", ("er", "or", "ar")),
    ("ing", ("ing",)), ("final_y", ("y",)), ("al", ("al",)),
    ("ence", ("ence", "ance")), ("ure", ("ure",)), ("ous", ("ous",)),
    ("ive", ("ive",)), ("ate", ("ate",)), ("age", ("age",)),
]


def _forced_split(word, _cache={}):
    """Split into known words without taking the whole word as one piece."""
    if word in _cache:
        return _cache[word]

    def go(i, depth):
        if i == len(word):
            return []
        if depth > 2:
            return None
        for j in range(len(word), i + 2, -1):
            if j - i == len(word):
                continue
            if word[i:j] in g2p._DICT and go(j, depth + 1) is not None:
                return [word[i:j]] + go(j, depth + 1)
        return None

    pieces = go(0, 1)
    _cache[word] = pieces if pieces and len(pieces) > 1 else None
    return _cache[word]


def tags_for(word, phones):
    """Auto-tag by spelling and by the phones, so the refit can score by tag."""
    found = []
    for tag, endings in SPELLING_TAGS:
        if any(word.endswith(e) for e in endings):
            found.append(tag)
    # g2p._split refuses to break a word CMUdict already knows, which is most
    # compounds. For tagging, break it anyway.
    if _forced_split(word):
        found.append("compound")
    if phones:
        bare = [p.rstrip("012") for p in phones]
        vowels = [i for i, p in enumerate(bare) if p in generate.syllabify.VOWELS]
        if vowels and len(bare[: vowels[0]]) > 1:
            found.append("cluster")
        if len(vowels) >= 4:
            found.append("long")
        if bare and bare[-1] in ("CH", "JH", "SH", "TH", "ZH"):
            found.append("coda_" + bare[-1].lower())
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("words", help="file with one word per line, or - for stdin")
    args = ap.parse_args()

    stream = sys.stdin if args.words == "-" else open(args.words, encoding="utf-8")
    with stream:
        words = []
        for line in stream:
            line = line.split("#", 1)[0]
            words += [w.lower() for w in line.split() if w.isalpha()]

    # Never ask for a word that is already reviewed.
    import csv as _csv

    existing = set()
    gold = ROOT / "data" / "eval_v0.csv"
    if gold.exists():
        with open(gold, encoding="utf-8") as f:
            existing = {r["word"] for r in _csv.DictReader(f)}
    words = [w for w in dict.fromkeys(words) if w not in existing]

    rows = []
    for word in words:
        phones = g2p.phones(word)
        ranked = generate.candidates(word, limit=4)
        spelled = letters.read(word)
        # The letter reading goes in alt_forms too: often it is the right one,
        # and then the review is a copy rather than a retype.
        alts = [r for r in ranked[1:] if r != ranked[0]] if ranked else []
        if spelled and spelled not in ranked:
            alts.insert(0, spelled)
        rows.append({
            "word": word,
            "arpabet": " ".join(phones) if phones else "",
            "vi_form": ranked[0] if ranked else "",
            "alt_forms": ";".join(alts[:4]),
            "vi_native": "",
            "tags": ";".join(tags_for(word, phones)),
            "confidence": "",
            "status": "generated",
        })

    # Group by tag so similar words sit together and review stays consistent.
    rows.sort(key=lambda r: (r["tags"], r["word"]))
    writer = csv.DictWriter(sys.stdout, fieldnames=FIELDS)
    writer.writeheader()
    for i, row in enumerate(rows, 1):
        writer.writerow({"id": f"g{i:04d}", **row})


if __name__ == "__main__":
    main()
