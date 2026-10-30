"""Milestone 1: every gold reading must survive parse -> render unchanged."""

import csv
from pathlib import Path

import pytest

from boi import vi

GOLD = Path(__file__).resolve().parents[1] / "data" / "eval_v0.csv"


def gold_forms():
    with open(GOLD, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            forms = [row["vi_form"]] + [a for a in row["alt_forms"].split(";") if a]
            for form in forms:
                yield row["word"], form


@pytest.mark.parametrize("word,form", list(gold_forms()))
def test_round_trip(word, form):
    assert vi.render_word(vi.parse_word(form)) == form, word


@pytest.mark.parametrize("word,form", list(gold_forms()))
def test_gold_rhymes_are_legal(word, form):
    """The phonotactic table must not reject a reading a native speaker wrote."""
    for syl in vi.parse_word(form):
        assert vi.is_legal(syl), f"{word}: {form} has rhyme {syl.nucleus}+{syl.coda!r}"
