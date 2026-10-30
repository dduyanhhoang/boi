"""Print the aligned phone -> Vietnamese counts, and flag what phonemap misses.

Dev only. A line marked DIFFERS means the mapping table's first choice is not
what the native speaker used most often, so either the table is wrong or those
words are lexical.

    uv run scripts/report_coverage.py
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from boi import align, phonemap  # noqa: E402

DEV = ROOT / "data" / "splits" / "dev.csv"


def table_first_choice(phone, role):
    if role == "onset":
        got = phonemap.ONSET.get(phone)
        return got[0][0] if got else None
    if role == "nucleus":
        got = phonemap.NUCLEUS_OPEN.get(phone)
        if not got:
            return None
        nucleus, offglide, _ = got[0]
        return nucleus + ("+" + offglide if offglide else "")
    options = phonemap.CODA.get(phone) or phonemap.CODA_RUNS.get(tuple(phone.split("+")))
    return options[0][0] or "(drop)" if options else None


def main():
    with open(DEV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    table, skipped = align.counts(rows)

    differs = 0
    for role in ("onset", "nucleus", "coda"):
        print(f"\n== {role} ==")
        for (phone, r), counter in sorted(table.items()):
            if r != role:
                continue
            gold = counter.most_common()
            mine = table_first_choice(phone, role)
            flag = ""
            if mine is not None and gold and gold[0][0] != mine:
                flag = f"   DIFFERS (table says {mine!r})"
                differs += 1
            shown = " ".join(f"{piece or '-'}:{n}" for piece, n in gold[:5])
            print(f"  {phone:10} -> {shown}{flag}")

    print(f"\n{differs} mappings where the table disagrees with the dev majority.")
    print("Expected for the context-dependent entries: the table picks ô or âu for")
    print("OW by position, c or ch for K by nucleus, and this report compares")
    print("against the context-free first choice.")
    if skipped:
        print(f"skipped (no phones or unparsable gold): {skipped}")


if __name__ == "__main__":
    main()
