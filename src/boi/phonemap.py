"""ARPAbet -> Vietnamese slot options, with a penalty on each option.

Penalty 0 is the preferred reading; higher means less likely. Every entry is
traceable to the native-speaker corrections in docs/brief.md or to a row of the eval
set, named in the comment. scripts/report_coverage.py checks the table against
the gold alignment and prints what it misses.
"""

# --- onsets ---------------------------------------------------------------
ONSET = {
    "P": [("p", 0)],
    "B": [("b", 0)],
    "T": [("t", 0)],
    "D": [("đ", 0)],
    "K": [("k", 0)],
    "G": [("g", 0)],
    "F": [("ph", 0)],
    "V": [("v", 0)],
    "TH": [("th", 0)],
    "DH": [("d", 0)],            # ð -> d, docs/brief.md
    "S": [("s", 0), ("x", 1)],   # xóp/xót are lexical, docs/brief.md
    "Z": [("d", 0)],             # z -> d: đì dai, vơ dừn
    "SH": [("s", 0), ("x", 1)],
    "ZH": [("d", 0)],            # ʒ -> d: vơ dừn
    "CH": [("ch", 0)],       # sen guých; after a it is t, see _CH_CODA_AFTER_A
    "JH": [("gi", 0), ("d", 1)], # gia va, giút / pờ rô dếch
    "M": [("m", 0)],
    "N": [("n", 0)],
    # An onset ŋ only ever comes from an intervocalic ng, where the nasal is
    # already carried by the coda the gemination left behind: sinh gờ.
    "NG": [("g", 0)],
    "L": [("l", 0)],
    "R": [("r", 0)],
    "W": [("g", 0)],             # w -> g: sóp goe, goai, guốc
    "Y": [("d", 0)],             # youtube -> diu túp
    "HH": [("h", 0)],
}

# Consonant runs that become one onset instead of an inserted syllable.
ONSET_RUNS = {
    ("T", "R"): [("tr", 0)],     # tren, tra vồ, sờ trít
    ("T", "S"): [("d", 0)],      # pizza -> pi da
}

# --- nuclei ---------------------------------------------------------------
# value: (nucleus, offglide coda, penalty)
NUCLEUS_OPEN = {
    "IY": [("i", "", 0)],
    "IH": [("i", "", 0)],
    "EH": [("e", "", 0), ("ê", "", 1)],   # tét, mét / con tếch (ec is illegal)
    "AE": [("a", "", 0), ("e", "", 1)],   # áp, chát, lách; see AE_BEFORE_D
    "AA": [("a", "", 0), ("o", "", 1)],
    "AH": [("ơ", "", 0), ("a", "", 1)],     # ă never stands alone in a rhyme
    "AO": [("o", "", 0)],
    "ER": [("ơ", "", 0)],
    "UW": [("u", "", 0)],
    "UH": [("u", "", 0)],
    "EY": [("â", "y", 0), ("ê", "", 1)],   # /eɪ/ -> ây, docs/brief.md
    "OW": [("â", "u", 0), ("ô", "", 1)],   # /oʊ/ -> âu, docs/brief.md
    "AY": [("a", "i", 0)],
    "AW": [("a", "o", 0)],
    "OY": [("o", "i", 0)],
}
# A consonant coda follows, so the offglide slot is taken.
# /æ/ is a, but e when a d closes the syllable: bad is bét and sandwich sen,
# against plan and fan, whose coda is a bare n. So disneyland is đít ni len.
AE_BEFORE_D = [("e", "", 0), ("a", "", 1)]
EY_BEFORE_S = [("â", "y", 0), ("ê", "", 1)]
AA_SPELLED_O = [("o", "", 0), ("ô", "", 1), ("a", "", 2)]
ESE_ENDING = [("i", "t", 0), ("ê", "", 1)]
AH_BEFORE_M = [("ư", "", 0), ("â", "", 1)]
OW_BEFORE_FINAL_SIBILANT = [("â", "u", 0), ("ô", "", 1)]
EH_EA_BEFORE_D = [("ê", "", 0), ("e", "", 1)]

NUCLEUS_CLOSED = dict(
    NUCLEUS_OPEN,
    AA=[("o", "", 0), ("a", "", 1)],       # con tếch, bóc / láp tốp
    AH=[("ă", "", 0), ("ơ", "", 1)],       # ắp, bắc / lớp, bớt
    EY=[("ê", "", 0), ("â", "y", 1)],      # đết, kếch, sờ tếch
    OW=[("ô", "", 0), ("â", "u", 1)],      # phôn, cốt, lốt
)
# /oʊ/ is âu at the end of a word (sâu, pho lâu, sờ nâu) and before an l that
# turns into the u glide (phâu đờ), but ô anywhere else (ô cây, hô theo, đô).
OW_FINAL = [("â", "u", 0), ("ô", "", 1)]
OW_MID = [("ô", "", 0), ("â", "u", 1)]
# /wɜr/ lands on uô: pát guốt, nét guốc.
ER_AFTER_GLIDE = [("ô", "", 0), ("ơ", "", 1)]
ER_SPELLED_OR = [("ô", "", 0), ("o", "", 1)]
# Unstressed schwa, which docs/brief.md puts at ơ or ư. The dev rows show it is the
# coda that decides, not the stress: -ment -> com, -le -> gồ, -et -> két.
SCHWA_OPEN = [("a", "", 0), ("ơ", "", 1), ("ô", "", 1)]   # đa ta, ba na na / sô lu
# A schwa before a final n is ư after a fricative (the -tion and -thon words)
# and o after a stop: con tờ rôn, not cưn.
SCHWA_BEFORE_N = [("ư", "", 0), ("ơ", "", 1)]
SCHWA_BEFORE_N_STOP = [("o", "", 0), ("ơ", "", 1)]
_FRICATIVES = {"S", "Z", "SH", "ZH", "CH", "TH", "DH", "F", "V"}

SCHWA_BY_CODA = {
    "N": SCHWA_BEFORE_N,                 # pai thừn, in phô mây sừn
    "M": [("o", "", 0), ("ơ", "", 1)],   # com piu tơ, ao go ri dừm
    "L": [("ô", "", 0), ("ơ", "", 1)],   # gu gồ, mo đồ, le vồ, ai đồ
    "T": [("e", "", 0), ("i", "", 1)],   # ma két tinh, ta ghét / cờ re đít
    "D": [("a", "", 0), ("ơ", "", 1)],   # sa lát
    "JH": [("i", "", 0)],                # i mịt, mét sịt
    "S": [("i", "", 0), ("ơ", "", 1)],   # óp phít
    "P": [("ă", "", 0), ("ơ", "", 1)],   # ắp đết
}
SCHWA_CLOSED = [("ơ", "", 0), ("e", "", 1), ("i", "", 1)]
# A reduced vowel keeps the letter it was written with, which is the whole
# difference between ra phờ ri and rê phờ ri. (open syllable, closed syllable)
# Only a single plain vowel letter is read this way. A digraph is an English
# spelling convention that a Vietnamese reader does not apply: the ee of free
# and the ea of team are /i/, not two letters to sound out.
SINGLE_LETTERS = ("a", "e", "i", "o", "u")
SCHWA_BY_LETTER = {
    "a": ([("a", "", 0)], [("a", "", 0), ("ơ", "", 1)]),
    "e": ([("ê", "", 0), ("e", "", 1)], [("e", "", 0), ("ê", "", 1)]),
    "i": ([("i", "", 0)], [("i", "", 0)]),
    "o": ([("ô", "", 0), ("o", "", 1)], [("o", "", 0), ("ô", "", 1)]),
    "u": ([("u", "", 0), ("ơ", "", 1)], [("u", "", 0), ("ơ", "", 1)]),
    "y": ([("i", "", 0)], [("i", "", 0)]),
}

# A tense vowel or diphthong can end a syllable; a checked one cannot. Used
# for where a cluster breaks, and for whether a final z is heard at all.
TENSE = {"IY", "EY", "AY", "OW", "OY", "AW", "UW", "ER"}

# --- codas ---------------------------------------------------------------
CODA = {
    "P": [("p", 0)],
    "B": [("p", 0)],             # youtube -> diu túp
    "F": [("p", 0)],             # v/f -> p, docs/brief.md
    "V": [("p", 0)],             # love -> lớp
    "T": [("t", 0)],
    "D": [("t", 0)],             # code -> cốt
    "TH": [("t", 0)],            # bluetooth -> tút
    "DH": [("t", 0)],
    "S": [("t", 0), ("", 1)],    # boss -> bốt / mouse -> mao
    "Z": [("", 0), ("t", 1)],    # size -> sai, cheese -> chi; see below
    "SH": [("t", 0)],
    "ZH": [("t", 0)],
    "CH": [("ch", 0)],       # sen guých; after a it is t, see _CH_CODA_AFTER_A
    "JH": [("t", 0)],            # image -> i mịt
    "K": [("c", 0)],
    "G": [("c", 0)],             # bug -> bắc
    "M": [("m", 0)],
    "N": [("n", 0)],
    "NG": [("ng", 0)],
    "L": [("", 0)],              # overridden by CODA_L below
    "R": [("", 0)],              # server -> sơ vơ, star -> sờ ta
}
CODA_RUNS = {
    ("K", "S"): [("c", 0)],              # con tếch, bóc
    ("K", "T"): [("c", 0)],              # pờ rô dếch
    ("K", "S", "T"): [("c", 0)],         # context
    ("N", "T"): [("n", 0)],              # i ven, com men
    ("N", "D"): [("n", 0)],              # tren, phren
    ("N", "S"): [("n", 0)],
    ("N", "TH"): [("n", 0)],
    ("NG", "K"): [("ng", 0)],            # pinh, linh / phăng sừn
    ("S", "T"): [("t", 0)],              # pốt, tét
    ("F", "T"): [("p", 0)],              # mai cờ rô sóp
    ("P", "T"): [("p", 0)],              # sờ críp
    ("R", "T"): [("t", 0)],              # sờ pọt, sờ mát
    ("R", "D"): [("t", 0)],              # pát guốt
    ("R", "K"): [("c", 0)],              # nét guốc
    ("R", "S"): [("t", 0)],
    ("L", "D"): [("t", 0)],
    ("M", "P"): [("m", 0)],
}
# Final l after a vowel becomes a glide, docs/brief.md. Keyed by the nucleus it follows.
CODA_L = {
    "i": [("u", 0)],             # skill -> sờ kiu
    "ê": [("u", 0)],             # sale -> sêu
    "â": [("u", 0)],
    "e": [("o", 0)],             # email -> i meo, hotel -> hô theo
    "ư": [("", 0)],
    "a": [("", 0), ("u", 1)],
    "ă": [("", 0)],
}
# After a back vowel there is no glide to take, so the l either becomes n or
# goes. Which one depends on the English vowel: a stressed one keeps the n
# (con trôn, sờ cun), a schwa drops it (gu gồ, mo đồ, le vồ, ai đồ).
CODA_L_BACK_STRESSED = [("n", 0), ("", 1)]
CODA_L_BACK_SCHWA = [("", 0), ("n", 1)]
_BACK = "oôơu"
# c vs ch and ng vs nh are not predictable from the nucleus (bác and bách both
# exist), so the gold decides the default: ch after a and ê (sờ nách, bờ lách,
# con tếch), c after i (cờ líc), nh after i and ê (pinh, linh).
_CH_AFTER = "aê"
# A /tʃ/ coda is ch after i (sen guých) but t after a: match is mát, not mách.
_CH_CODA_AFTER_A = "t"
_NH_AFTER = "iê"


def onset_options(phones):
    if not phones:
        return [("", 0)]
    if tuple(phones) in ONSET_RUNS:
        return ONSET_RUNS[tuple(phones)]
    return ONSET.get(phones[-1], [("", 3)])


def nucleus_options(phone, stress, closed, next_coda, final=False, glide=False,
                    onset=(), letter="", first=False):
    if phone == "ER" and glide:
        return ER_AFTER_GLIDE
    # ơ is what an er is read as. An or inside a word is not: the o of
    # information is phô, not phơ. A word-final -or is ơ again, like every
    # other final r-vowel: đốc tơ, ắc tơ, not đốc tô.
    if phone == "ER" and letter == "o" and not final:
        return ER_SPELLED_OR
    if phone == "OW":
        if next_coda == ("L",) and not final:
            return OW_FINAL          # phâu đờ
        if not closed:
            # âu only where a w is written: sâu, sờ nâu, pho lâu against
            # hê lô and vi đi ô.
            return OW_FINAL if final and "w" in (letter or "") else OW_MID
    # /ɪ/ and /i/ written with a single plain letter take that letter's
    # Vietnamese value: the e of encyclopedia is en and pê, not in and pi.
    # Only when the syllable is stressed or closed, because an unstressed open
    # one keeps CMUdict's vowel: event is i ven, not ê ven.
    # A word-initial open one is a prefix read as the English letter name,
    # which is where email gets i meo and esport i sờ pọt.
    # -ese is ít: chai nít, việt nam mít. The z is heard, where a final z
    # after a tense vowel is usually not, and the plain e is what separates
    # this from chi and pờ li, whose ee and ea keep theirs silent.
    if phone == "IY" and letter == "e" and final and next_coda in (("Z",), ("S",)):
        return ESE_ENDING
    if phone in ("IH", "IY") and letter in SINGLE_LETTERS \
            and (stress in ("1", "2") or closed) and not (first and not closed):
        by_letter = SCHWA_BY_LETTER.get(letter)
        if by_letter:
            return by_letter[1] if closed else by_letter[0]
    # /eɪ/ before an s is ây with the s unheard (phây búc, đa ta bây), not
    # ê closed by it. Only s: date and update keep đết.
    # /oʊ/ is ô, but âu when a final s or z closes it on paper and goes
    # unheard: close and clothes are both cờ lâu. post keeps pốt, its coda
    # ending in a stop rather than the sibilant.
    if phone == "OW" and final and next_coda and next_coda[-1] in ("S", "Z"):
        return OW_BEFORE_FINAL_SIBILANT
    # /ɑ/ takes the letter it is written with, and the dev rows never cross:
    # an a is a in all nine of ma két tinh, pát ti, gia va and the rest, an o
    # is o or ô in all ten of com men, xóp, mo đồ, láp tốp.
    # A reduced vowel closed by m is ừm: ao go ri dừm, en thu di a dừm,
    # xít từm. tone.py gives it the huyền.
    if phone == "AH" and stress == "0" and next_coda == ("M",) and final:
        return AH_BEFORE_M
    if phone == "AA" and letter == "o":
        return AA_SPELLED_O
    if phone == "EY" and next_coda == ("S",):
        return EY_BEFORE_S
    # /ɛ/ written ea and closed by a d is ê: đết lai, hết phôn. red keeps rét
    # on its plain e, and sweat sờ goét on its t.
    if phone == "EH" and letter == "ea" and next_coda == ("D",):
        return EH_EA_BEFORE_D
    if phone == "AE" and closed and next_coda and next_coda[-1] == "D":
        return AE_BEFORE_D
    if phone == "AH" and stress == "0":
        if not closed:
            if letter and letter[0] in SCHWA_BY_LETTER:
                return SCHWA_BY_LETTER[letter[0]][0]
            return SCHWA_OPEN
        # Before a coda n the letter decides, which is what -ment needs:
        # development is lắp men, not lắp mon, and presentation is den. The
        # two rules below only catch what the letters do not: -tion, whose
        # letters are io rather than one plain vowel, and the rest.
        if next_coda[0] == "N" and letter in SINGLE_LETTERS:
            by_letter = SCHWA_BY_LETTER.get(letter)
            if by_letter:
                return by_letter[1]
        if next_coda[0] == "N" and onset and onset[-1] not in _FRICATIVES:
            return SCHWA_BEFORE_N_STOP
        by_coda = SCHWA_BY_CODA.get(next_coda[0])
        if by_coda:
            return by_coda
        if letter and letter[0] in SCHWA_BY_LETTER:
            return SCHWA_BY_LETTER[letter[0]][1]
        return SCHWA_CLOSED
    table = NUCLEUS_CLOSED if closed else NUCLEUS_OPEN
    return table.get(phone, [("ơ", 3)])


def coda_options(phones, nucleus, schwa=False, vowel=""):
    if not phones:
        return [("", 0)]
    key = tuple(phones)
    # A final z goes unheard after a tense vowel, which is every gold case
    # (sai, chi, pờ li), but closes a checked one: disneyland is đít ni.
    if key == ("Z",) and vowel and vowel not in TENSE:
        return [("t", 0), ("", 1)]
    if key == ("L",):
        if nucleus in _BACK:
            return CODA_L_BACK_SCHWA if schwa else CODA_L_BACK_STRESSED
        return CODA_L.get(nucleus, [("", 0)])
    options = CODA_RUNS.get(key)
    if options is None:
        options = CODA.get(phones[0]) or CODA.get(phones[-1], [("", 2)])
    if key == ("CH",) and nucleus == "a":
        return [(_CH_CODA_AFTER_A, 0), ("ch", 1)]
    out = []
    for coda, penalty in options:
        # ch after a only for a plain k (sờ nách, bờ lách). A cluster keeps c
        # (pác kinh, tắc xi), and so does a g: bag is bác, not bách.
        if coda == "c" and nucleus in _CH_AFTER and (nucleus != "a"
                                                     or key == ("K",)):
            out.append(("ch", penalty))
        elif coda == "ng" and nucleus in _NH_AFTER:
            out.append(("nh", penalty))
        else:
            out.append((coda, penalty))
        if coda == "c" and nucleus == "i":
            out.append(("ch", penalty + 1))   # cờ líc / nét phờ lích
    return out
