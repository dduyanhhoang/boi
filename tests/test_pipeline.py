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
    ("esport", "i sờ pọt"),         # tense vowel stays open, s+p holds together
    ("offline", "óp lai"),          # checked vowel takes the f
    ("escape", "i sờ kếp"),
])
def test_known_reading(word, expected):
    got = generate.candidates(word, limit=5)
    assert expected in got, f"{word}: {expected!r} not in {got}"


# Known misses kept here so they are not mistaken for passing cases:
#   fashion -> pha sừn, gold phát sừn  (position and solution want no doubling
#                                     before a final -tion and outvote it)
#   speaker -> sờ píc cơ, gold sờ pích cơ
#   report -> ri pọt,  gold rì pọt  (docs/brief.md's pre-stress huyền, which the dev
#                                    rows contradict five times over)
#   game   -> ghêm,    gold gêm     (the gold ignores the gh spelling rule)
#   cool   -> cun,     gold cu      (school -> sờ cun has the same vowel and
#                                    stress, so no rule separates the two)


@pytest.mark.parametrize("word,expected", [
    # A single plain vowel letter is read as that letter.
    ("encyclopedia", "en sai cờ lô pê đi a"),
    ("refrigerator", "rê phờ ri giơ rây tơ"),  # not ra: the letter is an e
    ("camera", "ca mê ra"),                    # the r in ER0 opens the last one
    ("solution", "sô lu sừn"),   # the gold; it used to read sô lút sừn
    # A digraph keeps CMUdict's vowel, and an unstressed open one does too.
    ("free", "phờ ri"),
    ("team", "tim"),
    ("meeting", "mít tinh"),
    ("event", "i ven"),
    ("email", "i mêu"),
    # ơ is what an er is read as, not an or.
    ("information", "in phô mây sừn"),
    ("server", "sơ vơ"),
    ("burger", "bơ gơ"),
    # -y doubles only after a stressed syllable.
    ("responsibility", "ri sờ pon si bi li ti"),
    ("happy", "háp pi"),
    ("marketing", "ma két tinh"),
    # -tion is one piece wherever it sits, not only at the end of a word.
    ("international", "in tơ nát sừn nồ"),
    ("national", "nát sừn nồ"),
    ("additional", "a đít sừn nồ"),
    # and the letter decides before a coda n
    ("development", "đi ve lắp men"),
    ("government", "gơ vơ men"),
    # a /tʃ/ coda is t after a, ch after i
    ("match", "mát"),
    ("watch", "goát"),
    # a final z closes a checked vowel and goes unheard after a tense one
    ("disney", "đít ni"),
    ("size", "sai"),
    ("cheese", "chi"),
    # /æ/ is e when a d closes the syllable, a otherwise
    ("disneyland", "đít ni len"),
    ("bad", "bét"),
    ("sandwich", "sen guých"),
    ("plan", "pờ lan"),
    ("fan", "phan"),
    # /eɪ/ before an s is ây, the s unheard; a d still closes it
    ("facebook", "phây búc"),
    ("date", "đết"),
    # nothing doubles before a -tion syllable
    ("position", "pô di sừn"),
    ("solution", "sô lu sừn"),
])
def test_reduced_vowel_follows_the_spelling(word, expected):
    assert generate.read(word) == expected


def test_vowel_alignment_covers_most_of_the_gold():
    import csv
    from boi import spell as spell_mod

    path = Path(__file__).resolve().parents[1] / "data" / "eval_v0.csv"
    with open(path, encoding="utf-8") as f:
        words = [r["word"] for r in csv.DictReader(f)]
    aligned = sum(1 for w in words
                  if spell_mod.align_vowels(w, g2p.phones(w)) is not None)
    assert aligned >= 170, f"only {aligned}/{len(words)} words align"


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


@pytest.mark.parametrize("word,expected", [
    # Each of these is a correction the owner made by ear, pinned to the exact
    # first candidate rather than to the top five, because a rule that ranks
    # the right reading second is the bug they reported.
    ("facebook", "phây búc"),       # /eɪ/ before an s is ây, the s unheard
    ("date", "đết"),                # a d coda still closes it
    ("position", "pô di sừn"),      # nothing doubles before a final -tion
    ("solution", "sô lu sừn"),
    ("international", "in tơ nát sừn nồ"),   # but -tional keeps its doubling
    ("order", "o đờ"),              # a final -er, and the consonant before it
    ("folder", "phâu đờ"),
    ("teacher", "tít chờ"),         # plus a doubled /tʃ/ closing as t
    ("singer", "sinh gờ"),          # plus a doubled velar nasal
    ("computer", "com piu tơ"),
    ("server", "sơ vơ"),
    ("burger", "bơ gơ"),
    ("super", "súp pơ"),
    ("accurate", "a cu rết"),       # the same -ate       # nothing doubles into a yod
    ("taxi", "tắc xi"),             # lexicon: no rule predicts ă or x here
    ("bag", "bác"),                 # ch after a is for a plain k, not a g
    ("bug", "bắc"),
    ("match", "mát"),               # a real final /tʃ/ after a
    ("sandwich", "sen guých"),      # after i it keeps ch
    ("close", "cờ lâu"),            # /oʊ/ before an unheard final sibilant
    ("clothes", "cờ lâu"),
    ("post", "pốt"),                # a stop coda keeps ô
    ("phone", "phôn"),
    ("show", "sâu"),                # a written w decides âu against ô
    ("hello", "hê lô"),
    ("video", "vi đi ô"),
    ("headphone", "hết phôn"),      # ea closed by a d is ê
    ("red", "rét"),                 # a plain e is not
    ("sweat", "sờ goét"),           # nor is ea closed by a t
    ("family", "pham mi li"),       # a nasal doubles before a front letter
    ("comment", "com men"),
    ("learning", "lơn ninh"),
    ("camera", "ca mê ra"),         # but not before an open mid-word e
    ("drama", "đờ ra ma"),          # nor before an a
    ("banana", "ba na na"),
    ("opportunity", "o pô tun ni ti"),  # /ɑ/ takes its letter
    ("model", "mo đồ"),
    ("sorry", "so ri"),
    ("java", "gia va"),             # an a stays a
    ("marketing", "ma két tinh"),
    ("vietnamese", "việt nam mít"),  # lexicon: read as Vietnamese
    ("mechanic", "mê ca ních"),     # /ɪ/ never takes a doubled nasal
    ("mechanical", "mê ca ni cồ"),  # open or closed makes no difference
    ("comment", "com men"),         # /ɛ/ always does
    ("camera", "ca mê ra"),         # a schwa only where an i is written
    ("ticket", "tích két"),         # a doubled k after i is ch
    ("speaker", "sờ pích cơ"),
    ("netflix", "nét phờ lích"),    # and so is a cluster
    ("click", "cờ líc"),            # a plain one after a stressed vowel is c
    ("tiktok", "tíc tóc"),
    ("system", "xít từm"),          # lexicon for the x, rule for the ừm
    ("enthusiasm", "en thu di a dừm"),  # -sm is dừm, and the m is syllabic
    ("sarcasm", "sa ca dừm"),
    ("rhythm", "ri dừm"),
    ("capitalism", "cáp pi ta li dừm"),
    ("improvement", "im pờ rúp mừn"),   # -ment is ừn after a stressed syllable
    ("private", "pờ rai vết"),
    ("message", "mét sịt"),         # but -age is not: the coda decides
    ("movement", "múp mừn"),
    ("development", "đi ve lắp men"),   # and men after a reduced one
    ("time", "tham"),               # lexicon, for the th alone
    ("lifetime", "lai phờ tam"),    # the /aɪ/ before an m is the rule
    ("style", "sờ tai"),            # before every other coda it keeps it
    ("transliteration", "tran lít tơ rây sừn"),  # phones composed, reading derived
    ("generation", "gie nơ rây sừn"),  # an r before a stressed front vowel opens it
    ("operation", "o pơ rây sừn"),
    ("poweroff", "pao ơ óp"),       # but not before a back one: a compound
    ("overall", "âu vờ ron"),       # over- is âu, and the r opens all
    ("schedule", "sờ ke đùa"),      # by rule now, not memorised
    ("module", "mo đùa"),
    ("education", "e đu cây sừn"),  # the same đ, from the gold
    ("juice", "giút"),              # stressed, so gi
    ("bus", "bớt"),                 # /ʌ/ before s or v is ơ
    ("love", "lớp"),
    ("crush", "cờ rắt"),            # but not before every fricative
    ("temperature", "tem pơ rây chờ"),  # inserted ngang after a nasal; -ature
    ("template", "tem pờ lết"),     # -ate is ết, and the inserted ơ is huyền
    ("netflix", "nét phờ lích"),    # huyền after a stop coda
    ("icecream", "ai sờ cờ rim"),   # and after an open syllable
    ("paranoid", "pe ra noi"),      # an a not before -ture stays a
    ("english", "inh lích"),        # /ɪ/ before a velar nasal is always i
    ("link", "linh"),
    ("encyclopedia", "en sai cờ lô pê đi a"),   # elsewhere the letter decides
    ("conscious", "con sợt"),       # -ious is ợt
    ("delicious", "đi lít sợt"),
    ("friendly", "phờ ren li"),     # a voiced stop after a nasal still goes
    ("these", "di"),                # -ese is a suffix, not a whole word
    ("album", "ao bum"),            # a plain letter before m reads as itself
    ("problem", "pờ ro bờ lừm"),    # lexicon: the cluster, not the reading
    ("image", "i mịt"),             # the silent e of -age lengthens nothing
    ("chinese", "chai nít"),        # but -ese is a rule, not a lexicon entry
    ("japanese", "gia pa nít"),
    ("cheese", "chi"),              # ee keeps its z silent
    ("please", "pờ li"),            # and so does ea
    ("finance", "phai nan"),        # the variant that agrees with the letter
    ("image", "i mịt"),             # whose first vowel is not reduced
    ("livestream", "lai sờ trim"),  # a v after a tense vowel is unheard
    ("live", "lai"),
    ("icecream", "ai sờ cờ rim"),   # only a v, an s still gives sờ
    ("friendly", "phờ ren li"),     # a stop after a nasal coda is unheard
    ("handle", "han đồ"),           # unless a vowel follows, making it an onset
    ("raw", "ro"),                  # an aw is o, whichever vowel CMUdict lists
    ("reuse", "rì iu"),             # a /j/ between vowels is unheard
    ("overuse", "âu vờ iu"),        # and the syllable before it takes huyền
    ("use", "diu"),                 # word-initially it stays
])
def test_owner_corrections(word, expected):
    got = generate.candidates(word, limit=5)
    assert got and got[0] == expected, f"{word}: got {got}"


@pytest.mark.parametrize("misspelt,word", [
    ("dissneeland", "disneyland"),   # both doubled, one run at a time
    ("informattion", "information"),
    ("offliine", "offline"),         # only the ii is the mistake, not the ff
    ("scheedule", "schedule"),       # a lexicon entry keeps its reading
    ("taxxi", "taxi"),
    ("commeent", "comment"),
])
def test_a_doubled_letter_keeps_the_reading(misspelt, word):
    """A doubled letter is the commonest misspelling and the cheapest to undo.

    Without this the word falls past CMUdict to the spelling reader, which
    answers so differently that one stray letter changes the whole reading:
    scripts/check_robustness.py put that at 0.207 of 368 misspellings before
    g2p.undoubled and 0.935 after.
    """
    assert generate.candidates(misspelt, 1) == generate.candidates(word, 1)


def test_undoubled_only_answers_for_real_words():
    assert g2p.undoubled("informattion") == "information"
    assert g2p.undoubled("offliine") == "offline"
    assert g2p.undoubled("mousse") is None      # a word in its own right
    assert g2p.undoubled("disneyland") is None  # nothing doubled


@pytest.mark.parametrize("word,expected", [
    ("USB", "iu ét bi"),            # letter-named in CMUdict
    ("GPT", "gi pi ti"),            # not in CMUdict
    ("IT", "ai ti"),                # two letters always spell, even a real word
    ("AI", "ây ai"),
    ("HR", "ết a"),
    ("SMS", "ét em ét"),            # names stay whole, nothing resyllabifies
    ("SQL", "ét kiu eo"),
    ("KPI", "cây pi ai"),
    ("CEO", "xi i âu"),
    ("BMW", "bi em đáp bờ iu"),
    ("XYZ", "ích goai di"),
    ("HTML", "ết ti em eo"),
    ("HTTPS", "ết ti ti pi ét"),    # no vowel, so past the length limit
    ("GPS", "gi pi ét"),            # CMUdict has it as a word, wrongly
    ("IOS", "ai âu ét"),
    ("TV", "ti vi"),
])
def test_capitals_spell_out_letter_names(word, expected):
    assert generate.read(word) == expected


@pytest.mark.parametrize("word,expected", [
    ("ChatGPT", "chát gi pi ti"),   # a known word, then a capital tail
    ("iOS", "ai âu ét"),            # one lower-case letter takes its name
    ("eSIM", "e xim"),              # memorised, against the rule above
    ("MP3", "em pi ba"),
    ("4G", "bốn gi"),
    ("K8S", "cây tám ét"),
    ("A380", "ây ba tám không"),    # digit by digit
    ("HTML5", "ết ti em eo năm"),
    ("B2B", "bi tu bi"),            # memorised
    ("OK", "ô cây"),                # memorised: said as in okay, not âu cây
    ("VIP", "víp"),                 # memorised
])
def test_capital_tails_digits_and_memorised_forms(word, expected):
    assert generate.read(word) == expected


@pytest.mark.parametrize("word", [
    "NASA", "RAM", "DATA", "FREE",  # 3 or 4 letters CMUdict has as a word
    "LASER", "HELLO", "UNESCO",     # past the length limit
    "GIF", "JPEG", "ZALO",          # said as words, though CMUdict lacks them
    "A",                            # one letter is not an acronym
    "iPhone", "YouTube",            # capitals inside a word, not at its end
])
def test_capitals_that_are_read_as_words(word):
    assert generate.read(word) == generate.read(word.lower())


@pytest.mark.parametrize("word,expected", [
    ("usb", "diu ét bi"),           # lower case keeps the phones path
    ("it", "ít"),
])
def test_lower_case_is_not_an_acronym(word, expected):
    assert generate.read(word) == expected


def test_numbers_alone_are_not_acronyms():
    assert generate.read("2024") is None


@pytest.mark.parametrize("name", [*letters.NAMES.values(), *letters.DIGITS])
def test_letter_and_digit_names_are_legal_vietnamese(name):
    syls = vi.parse_word(name)
    assert all(vi.is_legal(s) for s in syls)
    assert vi.render_word(syls) == name
