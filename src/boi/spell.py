"""Read an unknown word off its spelling, as ARPAbet.

CMUdict covers 117k words and nothing else, so a brand or a coinage has no
pronunciation. This reads the letters instead, which is what a Vietnamese
speaker does with unfamiliar written English: logitech becomes lo-gi-tech
becomes lô di tếch.

The output is ARPAbet, not Vietnamese, so everything downstream (syllabify,
phonemap, tone, vi) stays the single source of truth for the Vietnamese side.
Accuracy here is well below CMUdict's; this path only runs when CMUdict and
the compound list both have nothing.
"""

VOWELS = "aeiouy"
# Appended to a vowel group that a silent e lengthens: "e" + this is the e
# of these, not the e of event.
LENGTHENED = "\u0304"

# Longest match first. A tuple means the grapheme decides from context.
CONSONANTS = {
    "tch": "CH", "sch": ("S", "K"), "ch": "CH", "sh": "SH", "th": "TH",
    "ph": "F", "wh": "W", "ck": "K", "ng": "NG", "qu": ("K", "W"),
    "gh": "G", "gn": "N", "kn": "N", "wr": "R", "ps": "S", "dg": "JH",
    "b": "B", "c": "K", "d": "D", "f": "F", "g": "G", "h": "HH", "j": "JH",
    "k": "K", "l": "L", "m": "M", "n": "N", "p": "P", "q": "K", "r": "R",
    "s": "S", "t": "T", "v": "V", "w": "W", "x": ("K", "S"), "z": "Z",
}
# c and g soften before e, i and y: logitech, cinema.
_SOFT = {"c": "S", "g": "JH"}
# Silent only where the word starts: pneumonia, pterodactyl, against the p
# of hypnosis and captain.
WORD_INITIAL = {"pn": "N", "pt": "T"}
# Two vowel letters that are no digraph are two syllables, ra-di-o and
# co-ni-o-sis, except an i after these, which is only a glide: na-tion,
# vi-sion, spe-cial, re-gion. After all but g the consonant turns palatal
# too, which is the sừn of every -tion: ti, ci, si and xi before a vowel are
# SH (ZH for a lone s after a vowel or r: vi-sion, ver-sion; CH for st:
# ques-tion), and the glide itself is a schwa. In 1,697 of 1,697 CMUdict
# words ending -tion or -sion the vowel is AH.
_GLIDE_I_AFTER = "cstxg"
_PALATAL = {"t": "SH", "c": "SH", "s": "SH", "x": ("K", "SH")}
# A final y or i is /i/ in English, and in bồi: háp pi, su si, mơ ni. Only a
# one-syllable word (fry, sky) and the -fy of fortify keep /aɪ/.
_FINAL_I_LETTERS = {"y", "i", "ey"}

# Vowel graphemes. (stressed, unstressed) ARPAbet, before an r-colour check.
DIGRAPHS = {
    "eau": "OW", "ee": "IY", "ea": "IY", "oo": "UW", "ou": "AW", "ow": "OW",
    "ai": "EY", "ay": "EY", "oi": "OY", "oy": "OY", "au": "AO", "aw": "AO",
    "ie": "IY", "ei": "EY", "eu": "UW", "ue": "UW", "ui": "UW", "oa": "OW",
    "oe": "OW", "ya": "AA", "yo": "OW", "ye": "IY", "ae": "EY",
    "aw": "AO", "ay": "EY", "ey": "EY", "oy": "OY", "ew": "UW", "uy": "AY",
    "ow": "OW",   # see _OW below: /aʊ/ unless it ends the word
}
# A w or y after a vowel belongs to the vowel group, not to the consonants.
_GLIDE_LETTERS = "wy"
# ow is /oʊ/ at the end of a word (slow, know, yellow) and /aʊ/ before a
# consonant (power, down, flower). Neither reading is rare, so position picks.
_OW = {"final": "OW", "other": "AW"}
# A single vowel letter: open syllable, then closed syllable. Open a is /eɪ/
# in English (name, data) but a reader meeting an unfamiliar word gives it the
# continental value, which is what the Vietnamese readings of brands show:
# lazada is la da đa, zalopay is da lô pây.
SINGLE = {
    "a": ("AA", "AE"), "e": ("IY", "EH"), "i": ("AY", "IH"),
    "o": ("OW", "AA"), "u": ("UW", "AH"), "y": ("AY", "IH"),
}
# Vowel plus r.
R_COLOURED = {"a": "AA", "o": "AO", "e": "ER", "i": "ER", "u": "ER", "y": "ER"}
# Vowel plus gh, where the gh is not a consonant at all: high, though, eight.
IRREGULAR = {"eigh": "EY", "ough": "AO", "augh": "AO", "igh": "AY"}
# Clusters English allows at the start of a syllable, so the whole run opens
# the next one rather than closing the one before: in-sta-gram, not instag-ram.
ONSET_CLUSTERS = {
    ("S", "T"), ("S", "P"), ("S", "K"), ("S", "L"), ("S", "M"), ("S", "N"),
    ("S", "W"), ("P", "L"), ("P", "R"), ("B", "L"), ("B", "R"), ("T", "R"),
    ("D", "R"), ("K", "L"), ("K", "R"), ("G", "L"), ("G", "R"), ("F", "L"),
    ("F", "R"), ("TH", "R"), ("SH", "R"), ("K", "W"),
}


def _graphemes(word):
    """Split into vowel groups and consonant graphemes, keeping order."""
    out, i = [], 0
    while i < len(word):
        chunk = next((word[i : i + n] for n in (4, 3)
                      if word[i : i + n] in IRREGULAR), None)
        if chunk:
            out.append(("v", chunk))
            i += len(chunk)
            continue

        if word[i] in VOWELS:
            j = i
            while j < len(word) and word[j] in VOWELS:
                j += 1
            # A y starting a vowel group is /j/; after one it belongs to it.
            if word[i] == "y" and j - i == 1 and j < len(word) and word[j] in VOWELS:
                out.append(("c", "Y"))
                i += 1
                continue
            # Absorb a following w or y when it completes a vowel digraph.
            if j < len(word) and word[j] in _GLIDE_LETTERS \
                    and word[i : j + 1] in DIGRAPHS:
                j += 1
            if _hiatus(word, i, j):
                out += [("v", word[i]), ("v", word[i + 1])]
            elif _glide(word, i, j):
                if out and out[-1][0] == "c":
                    out[-1] = ("c", _palatal(word, i, out))
                # The kind carries the palatal, which the vowel before wants.
                out.append(("g" + _palatal_letters(word, i), word[i:j]))
            else:
                out.append(("v", word[i:j]))
            i = j
            continue

        if i == 0 and word[:2] in WORD_INITIAL:
            out.append(("c", WORD_INITIAL[word[:2]]))
            i = 2
            continue

        for size in (3, 2, 1):
            piece = word[i : i + size]
            if piece in CONSONANTS:
                phones = CONSONANTS[piece]
                nxt = word[i + len(piece) : i + len(piece) + 1]
                # nxt is "" at the end of a word, and "" is a substring of
                # everything, so this has to test for a real letter first or
                # egg comes out as G JH.
                if piece in _SOFT and nxt and nxt in "eiy":
                    phones = _SOFT[piece]
                # A doubled letter is one sound: off, ball, kiss, shopee.
                # len(piece), not size: near the end of a word the slice is
                # shorter than size, and size would never read as 1.
                doubled = len(piece) == 1 and i and word[i - 1] == piece
                if not doubled:
                    out.append(("c", phones))
                i += len(piece)
                break
        else:
            i += 1  # a letter with no rule
    return out


def _hiatus(word, i, j):
    """Whether the vowel letters word[i:j] are two syllables rather than one."""
    pair = word[i:j]
    if len(pair) != 2 or pair in DIGRAPHS or pair in IRREGULAR:
        return False
    return not (pair[0] == "i" and i and (word[i - 1] in _GLIDE_I_AFTER
                                          or word[i - 2 : i] in ("sh", "ch")))


def _glide(word, i, j):
    """Whether word[i:j] is an i-glide after a palatal: the io of nation, the
    ia of special, the iou of delicious, the io of fashion."""
    group = word[i:j]
    if group[0] != "i" or len(group) not in (2, 3) or group in DIGRAPHS or group in IRREGULAR:
        return False
    return i > 0 and (word[i - 1] in _PALATAL or word[i - 2 : i] in ("sh", "ch"))


def _palatal_letters(word, i):
    """The palatal spelling before an i-glide at word[i]: t, st, c, s, ss, x, sh or ch."""
    two = word[i - 2 : i]
    return two if two in ("sh", "ch", "st", "ss") else word[i - 1]


def _palatal(word, i, out):
    """The phone the consonant before an i-glide at word[i] becomes."""
    letter = word[i - 1]
    if letter == "h":                       # sh and ch are palatal already
        return out[-1][1]
    if letter == "t" and word[i - 2 : i - 1] == "s":
        return "CH"                         # question, digestion
    if letter == "s" and word[i - 2 : i - 1] != "s" \
            and (word[i - 2 : i - 1] in VOWELS or word[i - 2 : i - 1] == "r"):
        return "ZH"                         # vision, version; not mission
    return _PALATAL[letter]


def _syllables(parts):
    """One syllable per vowel group: [onset phones, vowel letters, coda phones, palatal].

    palatal is the spelling before an i-glide group (t, st, c, s, ss, x, sh, ch), else "".
    """
    vowels = [i for i, (kind, _) in enumerate(parts) if kind[0] in "vg"]
    if not vowels:
        # No vowel at all (hmm, zzz). A reader still has to say something, so
        # the consonants get a schwa: the last one closes it, the rest open it.
        run = [p for _, p in parts]
        if not run:
            return []
        return [[run[:-1], "", run[-1:], False] if len(run) > 1 else [run, "", [], False]]
    syllables = []
    for n, i in enumerate(vowels):
        start = 0 if n == 0 else vowels[n - 1] + 1
        run = [p for _, p in parts[start:i]]
        # A run between two vowels either opens the next syllable whole, when
        # English allows it as an onset, or gives its first consonant to the
        # syllable before: lo-gi, in-sta-gram, tik-tok.
        if n and len(run) > 1 and tuple(_flatten(run[:2])) not in ONSET_CLUSTERS:
            syllables[-1][2].extend(run[:1])
            run = run[1:]
        coda = [p for _, p in parts[i + 1 :]] if n == len(vowels) - 1 else []
        syllables.append([run, parts[i][1], coda, parts[i][0][1:]])
    return syllables


def _flatten(phones):
    out = []
    for p in phones:
        out.extend(p if isinstance(p, tuple) else [p])
    return out


def phones(word):
    """ARPAbet with stress digits, read off the spelling. None if unreadable."""
    word = "".join(c for c in word.lower() if c.isalpha())
    if not word:
        return None

    silent_e = len(word) > 2 and word.endswith("e") and word[-2] not in VOWELS
    body = word[:-1] if silent_e else word

    syllables = _syllables(_graphemes(body))
    if not syllables:
        return None
    if silent_e:
        syllables[-1][2] = syllables[-1][2]  # the e only marks the vowel open

    last = len(syllables) - 1
    # English stresses the syllable before a palatal glide (in for MA tion),
    # and the reader knows that much: the first syllable steps down to 2.
    primary = next((n for n in range(1, last + 1) if syllables[n][3]), 1) - 1
    out = []
    for n, (onset, letters, coda, glide) in enumerate(syllables):
        if n == primary:
            stress = "1"
        elif glide:
            stress = "0"
        else:
            stress = "2" if n in (0, last) else "0"
        out += _flatten(onset)

        flat_coda = _flatten(coda)
        open_syllable = not flat_coda or (silent_e and n == len(syllables) - 1)
        base = letters[0] if letters else ""

        if glide:
            vowel = "AH"
        elif letters in IRREGULAR:
            vowel = IRREGULAR[letters]
        elif letters == "ow":
            vowel = _OW["final" if n == len(syllables) - 1 and not flat_coda
                        else "other"]
        elif letters in DIGRAPHS:
            vowel = DIGRAPHS[letters]
        elif flat_coda and flat_coda[0] == "R" and base in R_COLOURED:
            vowel = R_COLOURED[base]
        elif base in SINGLE:
            vowel = SINGLE[base][0 if open_syllable else 1]
        else:
            vowel = "AH"
        # An open i with an onset and a syllable after it is short, in 70% of
        # 7,554 CMUdict words (city, visit, silicon) and in bồi (vi rút, si li
        # con, pi da). A bare one keeps /aɪ/: icon, and the i of iPhone.
        if letters == "i" and open_syllable and onset and n < last:
            vowel = "IH"
        # An a before the t, c or lone s of a glide is /eɪ/ in 95% of 732
        # words: ây sừn, ây sồ, ây giừn. Not before sh or ss: fashion, passion.
        if letters == "a" and open_syllable and n < last and syllables[n + 1][3] in ("t", "c", "s"):
            vowel = "EY"
        if letters in _FINAL_I_LETTERS and n == last and open_syllable and last \
                and not (letters == "y" and body.endswith("fy")):
            vowel = "IY"
        # An unstressed open vowel reduces rather than lengthening: lo-gi.
        if stress == "0" and open_syllable and letters not in DIGRAPHS \
                and letters not in IRREGULAR:
            vowel = {"EY": "IH", "IY": "IY", "AY": "IH", "OW": "OW", "UW": "UW"}.get(vowel, vowel)
        out.append(vowel + stress)
        out += flat_coda
    return out


def align_vowels(word, phones):
    """Line the word's vowel letters up with its vowel phones, or None.

    CMUdict reduces an unstressed vowel to a schwa and loses which letter it
    was, but a Vietnamese reader keeps the letter: the re of refrigerator is
    re, not ra. Where the counts match, which is 173 of the 181 gold rows,
    this says which letters a phone came from.
    """
    word = "".join(c for c in word.lower() if c.isalpha())
    lengthened = len(word) > 2 and word.endswith("e") and word[-2] not in VOWELS
    if lengthened:
        word = word[:-1]

    groups, i = [], 0
    while i < len(word):
        if word[i] in VOWELS:
            j = i
            while j < len(word) and word[j] in VOWELS:
                j += 1
            groups.append(word[i:j])
            i = j
        else:
            i += 1

    vowels = [p for p in phones if p[:-1] in VOWEL_PHONES and p[-1].isdigit()]

    # A syllabic consonant is a vowel phone with no vowel letter: the schwa
    # of -sm, -thm and -ble is written nowhere. It is left out of the count
    # below and given an empty group afterwards, so the letters before it
    # still line up rather than the whole word losing its alignment.
    syllabic = (len(groups) < len(vowels) and len(vowels) > 1
                and vowels[-1] == "AH0" and phones[-1] in ("M", "N", "L")
                and word[-1] not in VOWELS)
    if syllabic:
        vowels = vowels[:-1]

    # A run of vowel letters can be more than one syllable: the ia of
    # encyclopedia is two phones, the eo of video is two. Split a run when the
    # phones ask for more, leaving the known digraphs (ea, ee, oo) whole.
    while len(groups) < len(vowels):
        for pool in (lambda g: len(g) > 1 and g not in DIGRAPHS,
                     lambda g: len(g) > 1):
            index = next((i for i, g in enumerate(groups) if pool(g)), None)
            if index is not None:
                groups[index : index + 1] = list(groups[index])
                break
        else:
            return None
    # More vowel letters than vowel phones means a silent one inside the word,
    # which is the e of improve before -ment. Only a lone e, and never the
    # first group, which is nobody's silent letter.
    while len(groups) > len(vowels) and "e" in groups[1:]:
        groups.pop(groups.index("e", 1))
    if len(groups) != len(vowels):
        return None
    if syllabic:
        groups.append("")
    # A silent e at the end lengthens the vowel before it, so that vowel is
    # read as the letter is named: these is di, not dê. Marked rather than
    # spelled out, so every other rule still sees the plain letter.
    elif lengthened and groups and len(groups[-1]) == 1:
        groups[-1] += LENGTHENED
    # A word-final w belongs to the vowel before it: show and snow are sâu
    # where hello and video are lô and ô, and only the w says so. Appended
    # after the counting above so it cannot be split as a run of letters.
    if groups and word.endswith("w") and len(word) > 1 and word[-2] in VOWELS:
        groups[-1] += "w"
    return groups


VOWEL_PHONES = {
    "AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY",
    "IH", "IY", "OW", "OY", "UH", "UW",
}
