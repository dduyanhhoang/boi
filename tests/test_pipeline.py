"""End-to-end checks on the rules that carry the most weight.

One case per rule, taken from the dev split, plus a floor on dev accuracy so a
refactor cannot quietly undo the tuning.
"""

import csv
from pathlib import Path

import pytest

from boi import generate, g2p, letters, lexicon, spell, syllabify, tone, vi

DEV = Path(__file__).resolve().parents[1] / "data" / "splits" / "dev.csv"
DEV_EXACT_FLOOR = 0.70


@pytest.mark.parametrize("word,expected", [
    ("online", "on lai"),           # maximal coda, not a cluster: on + lai
    ("street", "sờ trít"),          # s peels off, tr survives as one onset
    ("screen", "sờ cờ rin"),        # two inserted syllables
    ("software", "sóp goe"),        # w -> g plus the w-glide
    ("question", "quét chừn"),      # k + w -> qu, and -tion takes huyền
    ("context", "con tếch"),        # kst -> ch, and ec is illegal so e -> ê
    ("meeting", "mít tinh"),        # gemination before -ing
    ("office", "óp phít"),          # gemination of a voiceless consonant
    ("pizza", "pi da"),             # ts -> d, no coda
    ("computer", "com piu tơ"),     # yod after a labial survives
    ("sale", "sêu"),                # final l becomes the u glide
    ("google", "gu gồ"),            # final schwa + l drops
    ("control", "con trôn"),        # final l after a stressed vowel -> n
    ("sport", "sờ pọt"),            # nặng on a final -rt
    ("snack", "sờ nách"),           # k after a is spelled ch
])
def test_known_reading(word, expected):
    got = generate.candidates(word, limit=5)
    assert expected in got, f"{word}: {expected!r} not in {got}"


# Known misses kept here so they are not mistaken for passing cases:
#   taxi   -> tách si, gold tắc xi  (nucleus and coda both lexical)
#   report -> ri pọt,  gold rì pọt  (docs/brief.md's pre-stress huyền, which the dev
#                                    rows contradict five times over)
#   game   -> ghêm,    gold gêm     (the gold ignores the gh spelling rule)
#   cool   -> cun,     gold cu      (school -> sờ cun has the same vowel and
#                                    stress, so no rule separates the two)


def test_every_candidate_is_a_legal_syllable():
    for word in ("information", "schedule", "microsoft", "bluetooth", "netflix"):
        for form in generate.candidates(word, limit=5):
            for syl in vi.parse_word(form):
                assert vi.is_legal(syl), f"{word} -> {form}"


def test_lexicon_entries_are_legal_and_reachable():
    for word, form in lexicon.LEXICON.items():
        for syl in vi.parse_word(form):
            assert vi.is_legal(syl), f"{word} -> {form}"
        assert generate.read(word) == form


def test_inserted_syllable_takes_huyen():
    slots, _ = syllabify.variants(g2p.phones("street"))[0]
    assert slots[0].inserted
    assert tone.tone_of(slots[0], vi.Syl("s", "", "ơ", "")) == "huyen"


def test_unknown_word_without_g2p_en_is_none():
    assert g2p.phones("zzzqqq", predict=False) is None


@pytest.mark.parametrize("word,expected", [
    ("logitech", "lô di tếch"),     # read off the spelling: lo-gi-tech
    ("lazada", "la da đa"),         # open a takes its continental value
    ("zalopay", "da lô pây"),
    ("canva", "can va"),
    ("figma", "phíc ma"),
])
def test_word_read_off_its_spelling(word, expected):
    assert g2p.source(word) == "spelling"
    assert expected in generate.candidates(word, limit=3)


@pytest.mark.parametrize("word,pieces,expected", [
    ("poweroff", ["power", "off"], "pao ơ óp"),
    ("vinfast", ["vin", "fast"], "vin phát"),
    ("blackpink", ["black", "pink"], "bờ lách pinh"),
    ("grabfood", ["grab", "food"], "gờ ráp phút"),
    ("techcombank", ["tech", "com", "bank"], "tếch com bang"),
])
def test_compound_splits_into_known_words(word, pieces, expected):
    """Real phones for each half beat reading the letters."""
    assert g2p._split(word) == pieces
    assert expected in generate.candidates(word, limit=3)


@pytest.mark.parametrize("word,phones", [
    ("off", ["AA1", "F"]),          # a doubled letter at a word end is one sound
    ("ball", ["B", "AE1", "L"]),
    ("egg", ["EH1", "G"]),          # c and g only soften before a real e, i or y
    ("music", ["M", "UW1", "S", "IH2", "K"]),
    ("power", ["P", "AW1", "ER2", "R"]),   # ow is a vowel group, not o plus w
    ("slow", ["S", "L", "OW1"]),           # and it is /oʊ/ at a word end
    ("day", ["D", "EY1"]),
    ("new", ["N", "UW1"]),
])
def test_spelling_grapheme_rules(word, phones):
    assert spell.phones(word) == phones


@pytest.mark.parametrize("word,expected", [
    ("ecology", "ê cô lô gi"),      # e is ê, o is ô, final y is i
    ("medicine", "mê đi xin"),      # c before i is x, final e is silent
    ("power", "pao ơ"),             # ow is ao, er is r-coloured
    ("server", "sơ vơ"),
    ("street", "sờ trít"),          # no onset cluster: s peels off, tr stays
    ("project", "pờ rô giếch"),
    ("laptop", "láp tốp"),
    ("video", "vi đê ô"),
    ("banana", "ba na na"),
    ("camera", "ca mê ra"),
])
def test_letter_reading(word, expected):
    assert letters.read(word) == expected


def test_letter_reading_is_always_a_legal_syllable():
    for word in ("ecology", "medicine", "problem", "english", "strong",
                 "information", "google", "qwertyuiop"):
        for syl in vi.parse_word(letters.read(word)):
            assert vi.is_legal(syl), f"{word}: {letters.read(word)}"


def test_every_word_gets_a_reading():
    """The point of the spelling path: nothing comes back empty."""
    for word in ("qwertyuiop", "xyzzy", "brunchify", "ngocanh", "zzz"):
        assert generate.read(word), word


def test_spelling_syllables_do_not_duplicate_consonants():
    assert spell.phones("tiktok") == ["T", "IH1", "K", "T", "AA2", "K"]
    assert spell.phones("momo") == ["M", "OW1", "M", "OW2"]


def test_dev_exact_match_floor():
    with open(DEV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    hits = sum(generate.read(r["word"]) == r["vi_form"] for r in rows)
    rate = hits / len(rows)
    assert rate >= DEV_EXACT_FLOOR, f"dev exact match fell to {rate:.3f}"
