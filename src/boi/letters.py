"""Read an English word as if its letters were Vietnamese.

This is the second reading, not the default. A Vietnamese speaker who has
heard a word says it the way they heard it, which is what the rest of the
pipeline models from CMUdict; a speaker meeting it in writing sounds the
letters out with Vietnamese values. Both are real. On the 181 reviewed rows
the heard reading scores 0.707 and this one 0.420, so this one is offered
beside it rather than in place of it.

ecology is ê cô lô gi here, and medicine is mê đi xin.
"""

from . import vi

VOWELS = "aeiouy"

# Vowel groups. Single letters take their Vietnamese value: e is ê, o is ô.
NUCLEUS = {
    "a": ("a", ""), "e": ("ê", ""), "i": ("i", ""), "o": ("ô", ""),
    "u": ("u", ""), "y": ("i", ""),
    "ow": ("a", "o"), "ou": ("a", "o"), "au": ("a", "o"), "aw": ("a", "o"),
    "ay": ("â", "y"), "ai": ("a", "i"), "ey": ("â", "y"), "ei": ("ê", "i"),
    "oy": ("o", "i"), "oi": ("o", "i"), "oo": ("u", ""), "ee": ("i", ""),
    "ea": ("i", ""), "ie": ("i", ""), "oa": ("o", ""), "ue": ("u", ""),
    "ui": ("u", "i"), "eu": ("iê", "u"), "iu": ("i", "u"), "ua": ("uô", ""),
}

ONSET = {
    "ch": "ch", "ph": "ph", "th": "th", "sh": "s", "tr": "tr", "qu": "qu",
    "ck": "c", "ng": "ng", "gh": "g", "wh": "g", "kn": "n", "wr": "r",
    "b": "b", "c": "c", "d": "đ", "f": "ph", "g": "g", "h": "h", "j": "gi",
    "k": "c", "l": "l", "m": "m", "n": "n", "p": "p", "q": "qu", "r": "r",
    "s": "s", "t": "t", "v": "v", "w": "g", "x": "x", "y": "d", "z": "d",
}
# c before a front vowel: Vietnamese writes xi, not ci. g needs no rule,
# because onset g plus nucleus i already spells gi.
FRONTED = {"c": "x", "k": "c"}
# A w or y after a vowel joins the vowel group: power is pao, not pô-gê.
_GLIDE_LETTERS = "wy"

CODA = {
    "p": "p", "b": "p", "f": "p", "v": "p", "t": "t", "d": "t", "s": "t",
    "z": "t", "c": "c", "k": "c", "g": "c", "x": "c", "m": "m", "n": "n",
    "ng": "ng", "nh": "nh", "ch": "ch", "sh": "t", "th": "t", "ck": "c",
    "l": "u", "r": "", "h": "", "w": "o", "y": "i",
}
_STOPS = "ptcch"
# A vowel plus r is r-coloured, keyed on the Vietnamese nucleus the letter
# already became: power is pao ơ, server is sơ vơ, doctor is đốc tơ. Only a
# keeps its value, as in star and car.
R_COLOURED = {"ê": "ơ", "i": "ơ", "u": "ơ", "ô": "ơ", "ơ": "ơ", "a": "a"}
# English allows these to open a syllable, so the whole run goes to the onset.
ONSET_CLUSTERS = {"bl", "cl", "fl", "gl", "pl", "sl", "br", "cr", "dr", "fr",
                  "gr", "pr", "tr", "st", "sp", "sk", "sm", "sn", "sw", "tw"}


def _vowel_runs(group):
    """A run of vowel letters, split into the nucleus groups the table knows."""
    out, i = [], 0
    while i < len(group):
        for size in (2, 1):
            piece = group[i : i + size]
            if len(piece) == size and piece in NUCLEUS:
                out.append(piece)
                i += size
                break
        else:
            out.append(group[i])
            i += 1
    return out


def _chunks(word):
    """Split spelling into (onset letters, vowel letters, coda letters)."""
    groups, i = [], 0
    while i < len(word):
        if word[i] in VOWELS:
            j = i
            while j < len(word) and word[j] in VOWELS:
                j += 1
            if j < len(word) and word[j] in _GLIDE_LETTERS \
                    and word[i : j + 1] in NUCLEUS:
                j += 1
            groups.append(("v", word[i:j]))
            i = j
        else:
            j = i
            while j < len(word) and word[j] not in VOWELS:
                j += 1
            groups.append(("c", word[i:j]))
            i = j

    nuclei = []
    for n, (kind, text) in enumerate(groups):
        if kind != "v":
            continue
        for k, piece in enumerate(_vowel_runs(text)):
            nuclei.append((n, k, piece))
    if not nuclei:
        return [(word, "", "")] if word else []

    out = []
    for n, (group_index, place, piece) in enumerate(nuclei):
        run = ""
        if place == 0 and group_index and groups[group_index - 1][0] == "c":
            run = groups[group_index - 1][1]
            # One consonant opens the next syllable; a longer run gives its
            # first letter to the syllable before, unless the rest is a
            # cluster English can open with, which keeps it whole.
            if n and len(run) > 1 and run[-2:] not in ONSET_CLUSTERS:
                run = run[1:]
        coda = ""
        last_of_group = place == len(_vowel_runs(groups[group_index][1])) - 1
        if last_of_group and group_index + 1 < len(groups):
            tail = groups[group_index + 1][1]
            if n == len(nuclei) - 1:
                coda = tail
            elif len(tail) > 1 and tail[-2:] not in ONSET_CLUSTERS:
                # Exactly the letter the next syllable's onset gave up.
                coda = tail[:1]
        out.append((run, piece, coda))
    return out


def _onset(letters, nucleus):
    if not letters:
        return ""
    for size in (2, 1):
        if len(letters) < size:
            continue
        piece = letters[-size:]
        if piece in ONSET:
            if size == 1 and piece in FRONTED and nucleus and nucleus[0] in "iê":
                return FRONTED[piece]
            return ONSET[piece]
    return ""


def read(word):
    """The letter reading, or None when there is nothing to read."""
    word = "".join(c for c in word.lower() if c.isalpha())
    if not word:
        return None
    # A final e after a consonant is not pronounced: medicine is me-di-cin.
    # Except after l or r, where it carries its own syllable: goo-gle.
    if len(word) > 2 and word.endswith("e") and word[-2] not in VOWELS \
            and word[-2] not in "lr":
        word = word[:-1]

    syllables = []
    for onset_letters, vowel_letters, coda_letters in _chunks(word):
        # Vietnamese has no onset cluster: each extra consonant becomes its
        # own syllable, as in the main pipeline (pờ rô, bờ lu).
        while len(onset_letters) > 1 and onset_letters not in ONSET:
            head, onset_letters = onset_letters[0], onset_letters[1:]
            spelled = ONSET.get(head, "")
            if spelled:
                syllables.append(vi.Syl(spelled, "", "ơ", "", "huyen"))
        nucleus, offglide = NUCLEUS.get(vowel_letters,
                                        NUCLEUS.get(vowel_letters[:1], ("ơ", "")))
        onset = _onset(onset_letters, nucleus)
        if coda_letters[:1] == "r" and nucleus in R_COLOURED:
            nucleus, offglide, coda_letters = R_COLOURED[nucleus], "", coda_letters[1:]
        coda = offglide or CODA.get(coda_letters, CODA.get(coda_letters[:1], ""))
        # ch and nh are how c and ng are written after a front vowel.
        if coda == "c" and nucleus in "aê":
            coda = "ch"
        elif coda == "ng" and nucleus in "iê":
            coda = "nh"
        syl = vi.Syl(onset, "", nucleus, coda, "ngang")
        if not vi.is_legal(syl):
            syl = syl._replace(coda=offglide if vi.is_legal(
                syl._replace(coda=offglide)) else "")
        if syl.coda in _STOPS and syl.coda:
            syl = syl._replace(tone="sac")
        syllables.append(syl)
    return vi.render_word(syllables) if syllables else None
