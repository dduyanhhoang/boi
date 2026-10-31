"""The X-SAMPA decoder must produce real Vietnamese, or the benchmark lies."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))

import run_ngo  # noqa: E402

from boi import vi  # noqa: E402


def test_decoded_readings_round_trip():
    """Whatever the decoder emits has to be real quốc ngữ."""
    lines = (ROOT / "data" / "ngo" / "large_test.vie").read_text(
        encoding="utf-8").splitlines()
    checked = 0
    for line in lines[:400]:
        for reading in sorted(run_ngo.readings(line) or [])[:1]:
            assert vi.render_word(vi.parse_word(reading)) == reading, reading
            checked += 1
    assert checked > 350, f"only {checked} lines decoded"


def test_our_phonotactics_agree_with_theirs():
    """A cheap outside check on vi.LEGAL_CODAS.

    Their inventory is not ours and does not have to be, but a large gap would
    mean the table is wrong rather than strict. The known difference is éc,
    which this project leaves out so that context reads con tếch, the gold,
    rather than con téc.
    """
    lines = (ROOT / "data" / "ngo" / "large_test.vie").read_text(
        encoding="utf-8").splitlines()
    total = rejected = 0
    for line in lines:
        got = run_ngo.readings(line)
        if not got:
            continue
        for syl in vi.parse_word(sorted(got)[0]):
            total += 1
            rejected += not vi.is_legal(syl)
    assert total > 6000
    assert rejected / total < 0.02, (
        f"{rejected}/{total} of their syllables fall outside vi.LEGAL_CODAS")


def test_known_pairs_decode_as_expected():
    """The five words this set shares with data/eval_v0.csv."""
    expected = {
        "b_< @: _3 . r\\ a:U _1": "bờ rao",
        "k a: _1 . m e _1 . r\\ a: _1": "ca mê ra",
        "G @: _3 . r\\ i n _1": "gờ rin",
        "z a: _1 . v a: _1": "gia va",
    }
    for sampa, want in expected.items():
        assert want in run_ngo.readings(sampa), f"{sampa} -> {run_ngo.readings(sampa)}"
