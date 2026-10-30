"""The eval CSV must be reproducible from scripts/build_eval.py."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMITTED = ROOT / "data" / "eval_v0.csv"


def test_committed_csv_is_reproducible(tmp_path):
    out = tmp_path / "eval.csv"
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_eval.py"), str(out)],
        check=True,
    )
    assert out.read_bytes() == COMMITTED.read_bytes()


def test_every_row_has_phones_and_a_reading():
    rows = COMMITTED.read_text(encoding="utf-8").splitlines()[1:]
    assert len(rows) == 181
    for row in rows:
        f = row.split(",")
        assert f[2] and f[3], f"missing arpabet or vi_form: {row}"
