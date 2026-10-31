"""Fold a reviewed sheet back into the eval set.

The reviewer edits `vi_form` where the generated reading is wrong, leaves it
where it is right, and sets `status` to approved or corrected. Rows still
marked `generated` are treated as unreviewed and skipped, so a sheet can come
back in batches.

Every reading is parsed before it is accepted, which catches a typo that would
otherwise break the orthography round trip later.

    uv run scripts/merge_review.py data/review/sheet_001.csv
    uv run scripts/merge_review.py data/review/sheet_001.csv --dry-run
"""
import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from boi import vi  # noqa: E402

BUILD = ROOT / "scripts" / "build_eval.py"
REVIEWED = {"approved", "corrected"}


def check(row):
    """Complain about anything that would not survive the round trip."""
    problems = []
    if not row["vi_form"].strip():
        problems.append("empty vi_form")
    for label, text in [("vi_form", row["vi_form"])] + \
            [("alt_forms", a) for a in row["alt_forms"].split(";") if a]:
        try:
            syls = vi.parse_word(text)
        except ValueError as exc:
            problems.append(f"{label} {text!r}: {exc}")
            continue
        if vi.render_word(syls) != text:
            problems.append(f"{label} {text!r} does not round trip")
        for syl in syls:
            if not vi.is_legal(syl):
                problems.append(f"{label} {text!r}: {syl.nucleus}+{syl.coda!r} is not a"
                                " Vietnamese rhyme")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with open(args.sheet, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    reviewed = [r for r in rows if r["status"].strip().lower() in REVIEWED]
    skipped = len(rows) - len(reviewed)

    bad = [(r["word"], p) for r in reviewed for p in [check(r)] if p]
    if bad:
        print(f"{len(bad)} rows will not merge:", file=sys.stderr)
        for word, problems in bad:
            print(f"  {word}: {'; '.join(problems)}", file=sys.stderr)
        return 1

    source = BUILD.read_text(encoding="utf-8")
    known = {line.split("|")[0] for line in source.splitlines() if "|" in line}
    fresh = [r for r in reviewed if r["word"] not in known]

    lines = "\n".join(
        f"{r['word']}|{r['vi_form']}|{r['alt_forms']}|{r['tags']}|"
        f"{r['confidence'] or 'm'}" for r in fresh)
    corrected = sorted(r["word"] for r in fresh
                       if r["status"].strip().lower() == "corrected")

    print(f"{len(reviewed)} reviewed, {skipped} still marked generated, "
          f"{len(fresh)} new to add ({len(corrected)} corrected)")
    if args.dry_run or not fresh:
        return 0

    source = source.replace('\n""".strip()', f"\n{lines}\n\"\"\".strip()", 1)
    if corrected:
        source = source.replace('CORRECTED = set("""\n',
                                'CORRECTED = set("""\n' + " ".join(corrected) + "\n", 1)
    BUILD.write_text(source, encoding="utf-8")
    print(f"added to {BUILD.relative_to(ROOT)}; now run:")
    print("  uv run scripts/build_eval.py && uv run scripts/make_splits.py"
          " && uv run scripts/build_rhymes.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
