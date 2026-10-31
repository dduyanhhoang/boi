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
import itertools
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from boi import generate, g2p, letters  # noqa: E402

DATA = ROOT / "data" / "ngo"

TONES = {"_1": "", "_2": "́", "_3": "̀",
         "_4": "̉", "_5": "̃", "_6": "̣"}

# X-SAMPA onset -> the Vietnamese spellings it could be.
ONSETS = {
    "b_<": ["b"], "d_<": ["đ"], "t": ["t"], "t_h": ["th"], "k": ["k"],
    "p": ["p"], "m": ["m"], "n": ["n"], "N": ["ng"], "J\\": ["nh"],
    "f": ["ph"], "v": ["v"], "s": ["s", "x"], "z": ["d", "gi"],
    "h": ["h"], "x": ["kh"], "G": ["g"], "l": ["l"], "r\\": ["r"],
    "ts\\": ["ch", "tr"], "w": ["g"], "j": ["d"],
}
# X-SAMPA nucleus -> Vietnamese letters.
NUCLEI = {
    "a:": "a", "a": "ă", "@:": "ơ", "@": "â", "E": "e", "e": "ê",
    "O": "o", "o": "ô", "i": "i", "u": "u", "1": "ư",
    "a:I": "ai", "aI": "ay", "@I": "ây", "a:U": "ao", "aU": "au",
    "@U": "âu", "u@": "uô", "i@": "iê", "1@": "ươ", "iU": "iu",
    "EU": "eo", "eU": "êu", "OI": "oi", "oI": "ôi", "uI": "uy",
    "ui:": "ui", "Oa:": "oa", "OE": "oe", "i@U": "iêu", "ue": "uê",
}
CODAS = {"n": "n", "t": "t", "k": "c", "p": "p", "N": "ng", "m": "m",
         "J": "nh", "c": "ch", "l": "u", "h": "", "v": ""}
# The tone mark sits on the second letter of these, on the first of the rest.
_TWO_PART = ("iê", "uô", "ươ", "iêu")


def spell_onset(onset, nucleus):
    """c/k/qu and g/gh are decided by what follows, as everywhere else."""
    if onset == "k":
        return "k" if nucleus[0] in "ieê" else "c"
    if onset == "g":
        return "gh" if nucleus[0] in "ieê" else "g"
    return onset


def decode(syllable):
    """One X-SAMPA syllable -> every quốc ngữ spelling it could be."""
    parts = syllable.split()
    tone = TONES.get(parts[-1], "") if parts[-1].startswith("_") else ""
    body = [p for p in parts if not p.startswith("_")]
    if not body:
        return []

    onsets = [""]
    if body[0] in ONSETS and len(body) > 1:
        onsets = ONSETS[body[0]]
        body = body[1:]
    if not body or body[0] not in NUCLEI:
        return []
    nucleus = NUCLEI[body[0]]
    coda = "".join(CODAS.get(p, "?") for p in body[1:])
    if "?" in coda:
        return []

    i = 1 if nucleus in _TWO_PART else 0
    marked = unicodedata.normalize("NFC", nucleus[: i + 1] + tone + nucleus[i + 1:])
    return [spell_onset(o, nucleus) + marked + coda for o in onsets]


def readings(line):
    """One X-SAMPA word -> every quốc ngữ reading it could be, or None."""
    per_syllable = [decode(s) for s in line.strip().split(" . ")]
    if not all(per_syllable):
        return None
    if sum(len(s) for s in per_syllable) > 64:
        per_syllable = [s[:1] for s in per_syllable]
    return {" ".join(combo) for combo in itertools.product(*per_syllable)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--errors", action="store_true")
    ap.add_argument("--reading", choices=["heard", "letters", "either"],
                    default="heard", help="which reading to score")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--split", choices=["dev", "test", "all"], default="all",
                    help="every other word, so the letter reader can be fitted "
                         "on dev without spending test")
    args = ap.parse_args()

    words = [l.split("\t")[0].strip()
             for l in open(DATA / "large_test.lex", encoding="utf-8")]
    lines = open(DATA / "large_test.vie", encoding="utf-8").read().splitlines()

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
        heard = generate.read(word)
        spelled = letters.read(word)
        got = {"heard": heard, "letters": spelled,
               "either": heard if heard in allowed else spelled}[args.reading]
        total += 1
        if got in allowed:
            exact += 1
        elif len(misses) < 400:
            misses.append((word, got, sorted(allowed)[0], g2p.source(word)))

    print(f"Ngo et al. large_test [{args.split}] ({args.reading}): "
          f"{total} words scored, "
          f"{undecodable} could not be decoded")
    print(f"  agreement  {exact / total:.3f}  ({exact}/{total})")
    if args.errors:
        print()
        for word, got, want, source in misses[:40]:
            print(f"  {word:16} got {str(got):22} they say {want:22} {source}")


if __name__ == "__main__":
    main()
