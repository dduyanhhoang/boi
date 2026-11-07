"""English word -> ARPAbet phones with stress digits.

Three sources, in order of how much they can be trusted:

1. CMUdict, plus the handful of compounds it lacks.
2. A split into CMUdict words, for the compounds nobody lists: poweroff is
   power plus off, grabfood is grab plus food. Real phones, so this beats
   reading the letters whenever it finds a split. Failing a whole split, a
   long word that is mostly known words is read as those words, with only
   the letters between them read off the spelling.
3. g2p_en, if it is installed (`uv sync --extra oov`). docs/brief.md allows it
   only as this fallback; it pulls in numpy and nltk and downloads a tagger on
   first use, so it stays optional.
4. spell.py, which reads the letters. Always available, least accurate, and
   the reason no word comes back empty.
"""

import re

import cmudict

from . import spell

_DICT = cmudict.dict()
_G2P = None

# Words CMUdict lacks, hand-composed from the parts it does have.
COMPOUNDS = {
    "livestream": "L AY1 V S T R IY1 M",  # "live" as in /laɪv/, not /lɪv/
    "icecream": "AY1 S K R IY1 M",
    "tiktok": "T IH1 K T AA2 K",
    # The splitter cuts this as trans + lite + ration, three real words
    # across the wrong seams. trans plus the -literation of alliteration,
    # which CMUdict has right, so the rules read it from sound phones.
    "transliteration": "T R AE2 N Z L IH1 T ER0 EY2 SH AH0 N",
    "transliterated": "T R AE2 N Z L IH1 T ER0 EY2 T IH0 D",
}


# A piece shorter than this makes for junk splits: shopee is not shop plus ee.
_MIN_PIECE = 3
# Inside a word that is only partly known, shorter words turn up by chance:
# pneumono holds mono.
_MIN_KNOWN = 5


def _split(word, _cache={}):
    """Fewest, longest CMUdict words this word is made of, or None."""
    if word in _cache:
        return _cache[word]

    def go(i, depth):
        if i == len(word):
            return []
        if depth > 3:
            return None
        best = None
        for j in range(len(word), i + _MIN_PIECE - 1, -1):
            if word[i:j] in _DICT:
                rest = go(j, depth + 1)
                if rest is not None and (best is None or len(rest) + 1 < len(best)):
                    best = [word[i:j]] + rest
        return best

    pieces = go(0, 1)
    _cache[word] = pieces if pieces and len(pieces) > 1 else None
    return _cache[word]


def citation_table():
    """The nine CMUdict words whose citation form is not the one it lists first.

    Small enough to ship to the browser whole, which is why the shards carry
    one pronunciation per word and this sits beside them.
    """
    return {word: _citation(word) for word in _DICT
            if _citation(word) != _DICT[word][0]}


def _citation(piece):
    """The pronunciation a piece has when said alone.

    CMUdict lists the reduced form of a function word first, so and is
    AH0 N D before AE1 N D. A compound is a sequence of words said one after
    another, not a sentence, so each piece takes the stressed form it would
    have on its own: dissneeland ends in len, not lon.
    """
    entries = _DICT[piece]
    for entry in entries:
        if any(phone.endswith("1") for phone in entry):
            return entry
    return entries[0]


def _known_parts(word):
    """The word as the known words in it and the letters between, or None.

    For a long word nobody lists that is built from words somebody does:
    pneumonoultramicroscopicsilicovolcanoconiosis holds pneumo, ultra,
    microscopic and volcano. Longest word first, left to right. None unless
    known words make up at least half the letters, so a name is not mined
    for whatever dictionary words it happens to contain.
    """
    out, gap, i = [], "", 0
    while i < len(word):
        # A known word may not end inside a vowel digraph: shopee holds the
        # surname shope, which would leave efood to spell out of shopeefood.
        j = next((j for j in range(len(word), i + _MIN_KNOWN - 1, -1)
                  if word[i:j] in _DICT and word[j - 1 : j + 1] not in spell.DIGRAPHS), None)
        if j:
            out += [(gap, False)] if gap else []
            out.append((word[i:j], True))
            gap, i = "", j
        else:
            gap, i = gap + word[i], i + 1
    out += [(gap, False)] if gap else []
    known = sum(len(text) for text, is_word in out if is_word)
    return out if 2 * known >= len(word) and len(out) > 1 else None


def parts(word):
    """The pieces an unlisted word's phones are built from, as (letters, phones).

    A whole split into CMUdict words, or failing that its known words and the
    letters between them, read off the spelling. Only the first piece keeps
    primary stress. None for a word CMUdict lists, or one with neither.
    """
    w = word.lower()
    if w in _DICT or w in COMPOUNDS or undoubled(w):
        return None
    pieces = [(p, True) for p in _split(w)] if _split(w) else _known_parts(w)
    if not pieces:
        return None
    out = []
    for n, (text, is_word) in enumerate(pieces):
        said = _citation(text) if is_word else spell.phones(text) or []
        out.append((text, [p.replace("1", "2") if n and p.endswith("1") else p
                           for p in said]))
    return out


def _compound(word):
    """Phones for a split, whole or partial."""
    pieces = parts(word)
    return [p for _, said in pieces for p in said] if pieces else None


def _predicted(word):
    global _G2P
    if _G2P is None:
        try:
            from g2p_en import G2p
        except ImportError:
            return None
        _G2P = G2p()
    # g2p_en emits punctuation and spaces alongside phones; keep the phones.
    return [p for p in _G2P(word) if p[0].isalpha()] or None


def undoubled(word):
    """The word with each doubled letter collapsed, if that is a known word.

    A doubled letter is one sound, and doubling one is the commonest way a
    word gets misspelt: informattion, scheedule, dissney. Without this they
    fall past CMUdict to the spelling reader, which answers so differently
    that one stray letter changes the whole reading.
    """
    if word in _DICT:
        return None             # mousse is a word, not a misspelt mouse
    runs = [m.start() for m in re.finditer(r"(.)\1", word)]
    if not runs:
        return None
    # One run at a time first: offliine is offline, not ofline, and only the
    # doubled i was the mistake.
    for i in runs:
        candidate = word[:i] + word[i + 1:]
        if candidate in _DICT:
            return candidate
    collapsed = re.sub(r"(.)\1+", r"\1", word)
    return collapsed if collapsed != word and collapsed in _DICT else None


# The vowel each letter has when the letter is named: a is EY, i is AY. A
# reader who does not know the word says the letters, which is how finance
# becomes phai nan rather than phi nan.
_LETTER_NAME_VOWEL = {"a": "EY", "e": "IY", "i": "AY", "o": "OW", "u": "UW"}
_REDUCED = {"AH0", "IH0"}


def _spelled_out(word, entries):
    """A variant whose first vowel is the one its letter is named with.

    CMUdict lists finance reduced-first, as F AH0 N AE1 N S, because that is
    how it is said in running speech. The first vowel of the first syllable
    is the one a Vietnamese reader takes from the spelling, so where CMUdict
    offers a reading that agrees with the letter, that is the one to use.
    """
    first = next((p for p in entries[0] if p[-1].isdigit()), None)
    if first not in _REDUCED:
        return None
    groups = spell.align_vowels(word, entries[0])
    if not groups:
        return None
    wanted = _LETTER_NAME_VOWEL.get(groups[0])
    if not wanted:
        return None
    for entry in entries[1:]:
        vowel = next((p for p in entry if p[-1].isdigit()), None)
        if vowel and vowel[:-1] == wanted:
            return entry
    return None


# What CMUdict says when it spells a word out: USB is Y UW EH S B IY.
_LETTER_PHONES = {
    "a": "EY", "b": "B IY", "c": "S IY", "d": "D IY", "e": "IY", "f": "EH F",
    "g": "JH IY", "h": "EY CH", "i": "AY", "j": "JH EY", "k": "K EY", "l": "EH L",
    "m": "EH M", "n": "EH N", "o": "OW", "p": "P IY", "q": "K Y UW", "r": "AA R",
    "s": "EH S", "t": "T IY", "u": "Y UW", "v": "V IY", "w": "D AH B AH L Y UW",
    "x": "EH K S", "y": "W AY", "z": "Z IY",
}


def _letter_named(word):
    said = " ".join(_LETTER_PHONES[c] for c in word)
    return any(" ".join(p.rstrip("012") for p in entry) == said
               for entry in _DICT.get(word, []))


def ordinary_word(word):
    """CMUdict has this lower-case word, and not as the names of its letters."""
    return word in _DICT and not _letter_named(word)


def letter_named_words():
    """The short words CMUdict spells out, for the browser, which has no phones."""
    return sorted(w for w in _DICT if len(w) in (3, 4) and w.isascii() and w.isalpha()
                  and _letter_named(w))


def phones(word, predict=True):
    """Phones for any word. None only when there are no letters to read."""
    w = word.lower()
    if w in _DICT:
        return _spelled_out(w, _DICT[w]) or _DICT[w][0]
    if w in COMPOUNDS:
        return COMPOUNDS[w].split()
    if not predict:
        return None
    plain = undoubled(w)
    if plain:
        return _DICT[plain][0]
    return _compound(w) or _predicted(w) or spell.phones(w)


def source(word):
    """Which of the three sources answers for this word."""
    w = word.lower()
    if w in _DICT:
        return "cmudict"
    if w in COMPOUNDS:
        return "compound"
    if undoubled(w):
        return "cmudict"
    if _split(w) or _known_parts(w):
        return "compound"
    if _predicted(w):
        return "g2p_en"
    return "spelling"
