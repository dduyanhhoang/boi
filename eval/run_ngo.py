"""Score the generator against Ngo et al.'s 2,400 Vietnamese readings.

An outside reference. The data is proper names rather than the everyday
loanwords of data/eval_v0.csv, and it was produced for ASR rather than for
this, so it is a second opinion and not a target. No rule is fitted on it.

Their Vietnamese is X-SAMPA with tone numbers. Where the notation cannot tell
two Vietnamese spellings apart, which it cannot for s and x, or d and gi, or
ch and tr, the decoder returns both and either counts as a match.

These are names, which people meet in writing, so the letter reading is the
one to measure here: it scores 0.211 against CMUdict's 0.125, the opposite
way round from data/eval_v0.csv, where the loanwords people say give CMUdict
0.707 and the letters 0.420. Two independent sets, two opposite verdicts, one
for each reading. --split halves the data so letters.py can be fitted on dev
without spending test.

    uv run eval/run_ngo.py
    uv run eval/run_ngo.py --errors
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from boi import generate, g2p, letters, ngo  # noqa: E402

DATA = ROOT / "data" / "ngo"

readings = ngo.readings
DATA = ngo.DATA


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--errors", action="store_true")
    ap.add_argument("--reading", choices=["heard", "letters", "either"],
                    default="heard", help="which reading to score")
    ap.add_argument("--baseline", action="store_true",
                    help="score Ngo et al.'s own system output instead of ours")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--split", choices=["dev", "test", "all"], default="all",
                    help="every other word, so the letter reader can be fitted "
                         "on dev without spending test")
    args = ap.parse_args()

    words = [l.split("\t")[0].strip()
             for l in open(DATA / "large_test.lex", encoding="utf-8")]
    lines = open(DATA / "large_test.vie", encoding="utf-8").read().splitlines()
    # Their system's own predictions, decoded the same way and scored the same
    # way, so the comparison is like for like.
    theirs = open(DATA / "large_test.output", encoding="utf-8").read().splitlines()

    total = exact = undecodable = 0
    misses = []
    for n, (word, line) in enumerate(zip(words, lines)):
        if args.split == "dev" and n % 2:
            continue
        if args.split == "test" and not n % 2:
            continue
        if args.limit and total >= args.limit:
            break
        allowed = readings(line)
        if not allowed:
            undecodable += 1
            continue
        if args.baseline:
            predicted = readings(theirs[n]) or set()
            got = next(iter(predicted & allowed), sorted(predicted)[0] if predicted
                       else None)
        else:
            heard = generate.read(word)
            spelled = letters.read(word)
            got = {"heard": heard, "letters": spelled,
                   "either": heard if heard in allowed else spelled}[args.reading]
        total += 1
        if got in allowed:
            exact += 1
        elif len(misses) < 400:
            misses.append((word, got, sorted(allowed)[0], g2p.source(word)))

    label = "Ngo et al.'s own system" if args.baseline else args.reading
    print(f"Ngo et al. large_test [{args.split}] ({label}): "
          f"{total} words scored, "
          f"{undecodable} could not be decoded")
    print(f"  agreement  {exact / total:.3f}  ({exact}/{total})")
    if args.errors:
        print()
        for word, got, want, source in misses[:40]:
            print(f"  {word:16} got {str(got):22} they say {want:22} {source}")


if __name__ == "__main__":
    main()
