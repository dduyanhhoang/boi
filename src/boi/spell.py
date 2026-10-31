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
            out.append(("v", word[i:j]))
            i = j
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


def _syllables(parts):
    """One syllable per vowel group: (onset phones, vowel letters, coda phones)."""
    vowels = [i for i, (kind, _) in enumerate(parts) if kind == "v"]
    if not vowels:
        # No vowel at all (hmm, zzz). A reader still has to say something, so
        # the consonants get a schwa: the last one closes it, the rest open it.
        run = [p for _, p in parts]
        if not run:
            return []
        return [[run[:-1], "", run[-1:]] if len(run) > 1 else [run, "", []]]
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
        syllables.append([run, parts[i][1], coda])
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

    out = []
    for n, (onset, letters, coda) in enumerate(syllables):
        stress = "1" if n == 0 else ("2" if n == len(syllables) - 1 and n else "0")
        out += _flatten(onset)

        flat_coda = _flatten(coda)
        open_syllable = not flat_coda or (silent_e and n == len(syllables) - 1)
        base = letters[0] if letters else ""

        if letters in IRREGULAR:
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
    if len(word) > 2 and word.endswith("e") and word[-2] not in VOWELS:
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
    return groups if len(groups) == len(vowels) else None


VOWEL_PHONES = {
    "AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY",
    "IH", "IY", "OW", "OY", "UH", "UW",
}
