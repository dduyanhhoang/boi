"""Dump every linguistic table as JSON for the browser's unknown-word path.

GitHub Pages serves precomputed readings for the 117k words CMUdict knows.
Anything else has to be worked out in the browser, which means the pipeline
runs twice: once in Python, once in app/scripts/oov.js. Only the control flow
is written twice. Every table lives here, is generated from the Python
modules, and tests/test_js_conformance.py fails the build if the two
implementations ever disagree.

    uv run scripts/build_tables.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from boi import letters, lexicon, phonemap, rank, spell, syllabify, tone, vi  # noqa: E402
from boi.rhymes import RHYMES  # noqa: E402

OUT = ROOT / "app" / "data" / "tables.json"


def key(t):
    """A tuple key becomes a plus-joined string."""
    return "+".join(t) if isinstance(t, tuple) else t


def dict_keys(d):
    return {key(k): v for k, v in d.items()}


def main():
    tables = {
        "spell": {
            "vowels": spell.VOWELS,
            "consonants": {k: list(v) if isinstance(v, tuple) else [v]
                           for k, v in spell.CONSONANTS.items()},
            "soft": spell._SOFT,
            "digraphs": spell.DIGRAPHS,
            "single": {k: list(v) for k, v in spell.SINGLE.items()},
            "rColoured": spell.R_COLOURED,
            "irregular": spell.IRREGULAR,
            "onsetClusters": sorted(key(t) for t in spell.ONSET_CLUSTERS),
            "glideLetters": spell._GLIDE_LETTERS,
            "ow": spell._OW,
            "vowelPhones": sorted(spell.VOWEL_PHONES),
        },
        "syllabify": {
            "phoneVowels": sorted(syllabify.VOWELS),
            "clusterHeads": sorted(syllabify._CLUSTER_HEADS),
            "viOnsets": sorted(key(t) for t in syllabify._VI_ONSETS),
            "onsetRunsKeep": sorted(key(t) for t in syllabify.ONSET_RUNS_KEEP),
            "geminates": sorted(syllabify._GEMINATES),
            "voiceless": sorted(syllabify._VOICELESS),
            "keepsOffglide": sorted(syllabify._KEEPS_OFFGLIDE),
            "offglideNuclei": sorted(syllabify._OFFGLIDE_NUCLEI),
            "insertedNucleus": syllabify._INSERTED_NUCLEUS,
            "sClusters": sorted(key(t) for t in syllabify._S_CLUSTERS),
            "tense": sorted(syllabify._TENSE),
        },
        "phonemap": {
            "onset": phonemap.ONSET,
            "onsetRuns": dict_keys(phonemap.ONSET_RUNS),
            "nucleusOpen": phonemap.NUCLEUS_OPEN,
            "nucleusClosed": phonemap.NUCLEUS_CLOSED,
            "owFinal": phonemap.OW_FINAL,
            "owMid": phonemap.OW_MID,
            "erAfterGlide": phonemap.ER_AFTER_GLIDE,
            "schwaOpen": phonemap.SCHWA_OPEN,
            "schwaByCoda": phonemap.SCHWA_BY_CODA,
            "schwaClosed": phonemap.SCHWA_CLOSED,
            "schwaByLetter": {k: list(v) for k, v in phonemap.SCHWA_BY_LETTER.items()},
            "singleLetters": list(phonemap.SINGLE_LETTERS),
            "schwaBeforeN": phonemap.SCHWA_BEFORE_N,
            "schwaBeforeNStop": phonemap.SCHWA_BEFORE_N_STOP,
            "fricatives": sorted(phonemap._FRICATIVES),
            "coda": phonemap.CODA,
            "codaRuns": dict_keys(phonemap.CODA_RUNS),
            "codaL": phonemap.CODA_L,
            "codaLBackStressed": phonemap.CODA_L_BACK_STRESSED,
            "codaLBackSchwa": phonemap.CODA_L_BACK_SCHWA,
            "back": phonemap._BACK,
            "chAfter": phonemap._CH_AFTER,
            "nhAfter": phonemap._NH_AFTER,
        },
        "vi": {
            "toneMarks": vi.TONE_MARKS,
            "legalCodas": {k: sorted(v) for k, v in vi.LEGAL_CODAS.items()},
            "twoPart": sorted(vi._TWO_PART),
            "glideOBefore": sorted(vi._GLIDE_O_BEFORE),
            "glideUBefore": sorted(vi._GLIDE_U_BEFORE),
            "clusters": vi.CLUSTERS,
        },
        "tone": {
            "stopCodas": sorted(tone._STOP_CODAS),
            "sibilants": sorted(tone._SIBILANTS),
            "nangCodas": sorted(key(t) for t in tone._NANG_CODAS),
        },
        "rank": {
            "illegalOnset": rank._ILLEGAL_ONSET,
            "unseenRhyme": rank._UNSEEN_RHYME,
            "rhymes": sorted(f"{n}|{c}" for n, c in RHYMES),
        },
        "generate": {"budget": 3.0, "perSlot": 4},
        "letters": {
            "vowels": letters.VOWELS,
            "nucleus": {k: list(v) for k, v in letters.NUCLEUS.items()},
            "onset": letters.ONSET,
            "fronted": letters.FRONTED,
            "coda": letters.CODA,
            "rColoured": letters.R_COLOURED,
            "onsetClusters": sorted(letters.ONSET_CLUSTERS),
            "glideLetters": letters._GLIDE_LETTERS,
            "stops": letters._STOPS,
        },
        "lexicon": lexicon.LEXICON,
    }
    # app/data is generated and gitignored, so a fresh checkout has no
    # directory to write into.
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(tables, ensure_ascii=False, separators=(",", ":")),
                   encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)}  {OUT.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
