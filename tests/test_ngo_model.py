"""The reimplementation has to match the paper where the paper is explicit."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from boi import ngo, ngo_model, vi  # noqa: E402

# Figure 4 of arXiv:1810.03184 works DISNEYLAND through by hand.
FIGURE_4_READING = "d_< i _1 . s @: _3 . n i _1 . l E n _1"
FIGURE_4_LABELS = ["O", "N", "ON", "O", "N", "N", "O", "N", "Cd", "X"]


def test_figure_4_slot_structure():
    slots = ngo_model.target_slots(FIGURE_4_READING)
    assert [role for role, _ in slots] == ["O", "N", "O", "N", "O", "N",
                                           "O", "N", "Cd"]


def test_figure_4_label_derivation():
    """The labels the paper draws for DISNEYLAND, derived from its reading."""
    slots = ngo_model.target_slots(FIGURE_4_READING)
    assert ngo_model.derive_labels("disneyland", slots) == FIGURE_4_LABELS


def test_figure_4_pseudo_syllables():
    """s1={D,I} s2={S,@:} s3={N,EY} s4={L,A,N}, Section III-A-2."""
    units = ngo_model.units_from_labels(
        "disneyland", ["D", "IH", "Z", "N", "IY", "_", "L", "AE", "N", "DD"],
        FIGURE_4_LABELS)
    assert [(u["og"], u["ng"], u["cg"]) for u in units] == [
        ("d", "i", ""), ("s", "", ""), ("n", "ey", ""), ("l", "a", "n")]
    assert units[1]["epenthetic"]


def test_it_reads_real_words():
    import cmudict

    pronunciations = cmudict.dict()
    for word in ("camera", "disneyland", "laptop", "buffet"):
        got = ngo_model.read(word, pronunciations[word][0])
        assert got, word
        for reading in got:
            assert vi.render_word(vi.parse_word(reading)) == reading
