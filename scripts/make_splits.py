"""Split the eval set into dev and test, stratified so every tag appears in both.

Deterministic: seeded shuffle, no arguments. Thirteen tags occur exactly once
in the whole set and cannot appear in both halves; those rows go to dev, so
test stays a clean sample and the rare material stays available for rule work.

    uv run scripts/make_splits.py
"""
import collections
import csv
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "data" / "eval_v0.csv"
OUT = ROOT / "data" / "splits"
TEST_SIZE = 50
SEED = 0


def tags_of(row):
    return [t for t in row["tags"].split(";") if t]


def split(rows):
    counts = collections.Counter(t for r in rows for t in tags_of(r))
    singleton = {t for t, n in counts.items() if n == 1}

    pool = [r for r in rows if not (set(tags_of(r)) & singleton)]
    random.Random(SEED).shuffle(pool)

    test = {}
    # Rarest tags first, so a tag with two rows gets its one test row before a
    # common tag takes it.
    for tag in sorted(counts, key=lambda t: counts[t]):
        if tag in singleton or any(tag in tags_of(r) for r in test.values()):
            continue
        for row in pool:
            if tag in tags_of(row) and row["id"] not in test:
                # Leave at least one row of this tag behind for dev.
                if sum(1 for r in pool if tag in tags_of(r) and r["id"] not in test) > 1:
                    test[row["id"]] = row
                break

    for row in pool:
        if len(test) >= TEST_SIZE:
            break
        test.setdefault(row["id"], row)

    dev = [r for r in rows if r["id"] not in test]
    test = [r for r in rows if r["id"] in test]
    return dev, test


def main():
    with open(GOLD, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields, rows = reader.fieldnames, list(reader)

    dev, test = split(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    for name, part in (("dev", dev), ("test", test)):
        with open(OUT / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(part)

    dev_tags = {t for r in dev for t in tags_of(r)}
    test_tags = {t for r in test for t in tags_of(r)}
    print(f"dev {len(dev)}  test {len(test)}")
    print(f"tags in both: {len(dev_tags & test_tags)}")
    print(f"dev only: {sorted(dev_tags - test_tags)}")
    missing = sorted(test_tags - dev_tags)
    if missing:
        print(f"ERROR: tags only in test: {missing}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
