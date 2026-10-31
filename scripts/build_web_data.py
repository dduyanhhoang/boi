"""Precompute readings for every CMUdict word, for the static playground.

GitHub Pages cannot run Python, so the generator runs here and the browser
only looks the answer up. Output goes to app/data: one shard per first letter,
plus gold.json for the 181 reviewed words and index.json for the chrome.

    uv run scripts/build_web_data.py
"""
import csv
import json
import sys
from pathlib import Path

import cmudict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from boi import g2p, generate  # noqa: E402

OUT = ROOT / "app" / "data"
GOLD = ROOT / "data" / "eval_v0.csv"
SPLITS = ROOT / "data" / "splits"
TOP_N = 3
# Shown as starting chips: one per flavour of the problem, all with gold forms.
EXAMPLES = ["information", "software", "context", "schedule", "google",
            "sandwich", "question", "icecream", "netflix", "sale"]


def write(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                    encoding="utf-8")
    return path.stat().st_size


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pronunciations = cmudict.dict()

    # COMPOUNDS holds the words CMUdict lacks, icecream among them, and it is
    # on the example chips. Iterating cmudict alone used to drop all three.
    vocabulary = sorted(
        {w for w in pronunciations if w.isalpha()} | set(g2p.COMPOUNDS))

    shards, total = {}, 0
    for word in vocabulary:
        readings = generate.candidates(word, limit=TOP_N)
        if not readings:
            continue
        phones = " ".join(g2p.phones(word, predict=False))
        # The page shows the reading and derives the rest in the browser, so
        # a shard carries the phones and the readings and nothing it never
        # displays. The Ngo readings used to ride along as two more fields,
        # a third of every shard, after the page stopped showing them.
        shards.setdefault(word[0], {})[word] = f"{phones}|{';'.join(readings)}"
        total += 1

    size = 0
    counts = {}
    for letter, words in sorted(shards.items()):
        size += write(OUT / f"{letter}.json", words)
        counts[letter] = len(words)

    # Membership index for compound splitting in the browser. Words only, no
    # phones, so it is smaller than a single shard and one fetch covers every
    # split. app/scripts/oov.js runs the same algorithm as g2p._split.
    index = sorted(w for w in vocabulary if len(w) >= 3)
    (OUT / "words.txt").write_text("\n".join(index), encoding="utf-8")
    size += (OUT / "words.txt").stat().st_size

    # The review tool reads the open sheet from here.
    sheet = ROOT / "data" / "review" / "sheet_001.csv"
    if sheet.exists():
        (OUT / "review.csv").write_text(sheet.read_text(encoding="utf-8"),
                                        encoding="utf-8")
        size += (OUT / "review.csv").stat().st_size

    split_of = {}
    for name in ("dev", "test"):
        with open(SPLITS / f"{name}.csv", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                split_of[row["word"]] = name

    gold = {}
    with open(GOLD, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            gold[row["word"]] = {
                "vi": row["vi_form"],
                "alt": [a for a in row["alt_forms"].split(";") if a],
                "native": row["vi_native"],
                "tags": [t for t in row["tags"].split(";") if t],
                "status": row["status"],
                "split": split_of.get(row["word"], ""),
            }
    size += write(OUT / "gold.json", gold)

    agree = sum(1 for w, g in gold.items()
                if (generate.read(w) or "") in {g["vi"], *g["alt"]})
    size += write(OUT / "index.json", {
        "words": total,
        "counts": counts,
        "examples": EXAMPLES,
        "gold": len(gold),
        "agree": agree,
    })
    print(f"{total} words, {len(gold)} gold ({agree} agreeing) "
          f"-> {OUT.relative_to(ROOT)}  {size / 1e6:.1f} MB raw")


if __name__ == "__main__":
    main()
