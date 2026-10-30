"""Score the generator against a split.

    uv run eval/run_eval.py dev        # default
    uv run eval/run_eval.py test       # milestones only
    uv run eval/run_eval.py dev --errors

Reports exact match on vi_form, match on vi_form or any alt_form, top-5,
syllable error rate, tone accuracy, and a breakdown by tag.
"""
import argparse
import collections
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from boi import generate, lexicon, vi  # noqa: E402

SPLITS = Path(__file__).resolve().parents[1] / "data" / "splits"
TOP_K = 5


def edits(a, b):
    """Levenshtein over two lists."""
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def tones(form):
    try:
        return [s.tone for s in vi.parse_word(form)]
    except ValueError:
        return []


def bases(form):
    """Syllables with the tone taken off, so tone can be scored on its own."""
    try:
        return [s._replace(tone="ngang") for s in vi.parse_word(form)]
    except ValueError:
        return []


def evaluate(rows):
    stats = collections.Counter()
    by_tag = collections.defaultdict(collections.Counter)
    tone_hits = tone_total = syl_edits = syl_total = 0
    misses = []

    for row in rows:
        gold = row["vi_form"]
        alts = [a for a in row["alt_forms"].split(";") if a]
        ranked = generate.candidates(row["word"], limit=TOP_K)
        top = ranked[0] if ranked else ""

        exact = top == gold
        any_form = top in {gold, *alts}
        in_top_k = bool({gold, *alts} & set(ranked))

        stats["n"] += 1
        stats["exact"] += exact
        stats["any"] += any_form
        stats["topk"] += in_top_k
        for tag in (t for t in row["tags"].split(";") if t):
            by_tag[tag]["n"] += 1
            by_tag[tag]["exact"] += exact

        gold_syls, top_syls = bases(gold), bases(top)
        syl_edits += edits(top_syls, gold_syls)
        syl_total += len(gold_syls)

        gold_tones, top_tones = tones(gold), tones(top)
        if len(gold_tones) == len(top_tones):
            tone_hits += sum(a == b for a, b in zip(gold_tones, top_tones))
            tone_total += len(gold_tones)

        if not exact:
            misses.append((row["word"], gold, top, ";".join(alts), row["tags"]))

    n = stats["n"]
    return {
        "n": n,
        "exact": stats["exact"] / n,
        "any": stats["any"] / n,
        f"top{TOP_K}": stats["topk"] / n,
        "syl_error_rate": syl_edits / syl_total,
        "tone_accuracy": tone_hits / tone_total if tone_total else 0.0,
    }, by_tag, misses


def without_lexicon():
    """Context manager that empties the lexicon for the duration."""
    import contextlib

    @contextlib.contextmanager
    def swap():
        saved = dict(lexicon.LEXICON)
        lexicon.LEXICON.clear()
        try:
            yield
        finally:
            lexicon.LEXICON.update(saved)

    return swap()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("split", nargs="?", default="dev", choices=["dev", "test"])
    ap.add_argument("--errors", action="store_true", help="list every miss")
    ap.add_argument("--tags", action="store_true", help="per-tag exact match")
    args = ap.parse_args()

    with open(SPLITS / f"{args.split}.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    summary, by_tag, misses = evaluate(rows)
    with without_lexicon():
        rules_only, _, _ = evaluate(rows)

    memorised = sorted(w for w in lexicon.LEXICON
                       if w in {r["word"] for r in rows})
    print(f"{args.split}: {summary['n']} words")
    for key, value in summary.items():
        if key == "n":
            continue
        bare = rules_only[key]
        suffix = f"   (rules only {bare:.3f})" if abs(bare - value) > 1e-9 else ""
        print(f"  {key:16} {value:.3f}{suffix}")
    if memorised:
        print(f"  {len(memorised)} of these are lexicon entries: {', '.join(memorised)}")

    if args.tags:
        print("\nexact match by tag (worst first)")
        ranked = sorted(by_tag.items(), key=lambda kv: kv[1]["exact"] / kv[1]["n"])
        for tag, c in ranked:
            print(f"  {tag:14} {c['exact']}/{c['n']}")

    if args.errors:
        print(f"\n{len(misses)} misses")
        for word, gold, top, alts, tags in misses:
            print(f"  {word:14} gold={gold:20} got={top:20} alt={alts:16} {tags}")


if __name__ == "__main__":
    main()
