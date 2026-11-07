"""The browser pipeline must agree with the Python one, word for word.

app/scripts/oov.js reruns the pipeline for words the precomputed shards do
not have. Its tables are generated from the Python modules, but its control
flow is written twice, so this test runs both over a few thousand words and
fails on the first disagreement. Without it, the two drift apart silently.
"""

import json
import random
import shutil
import string
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from boi import g2p, generate, letters, spell, syllabify, tone, vi  # noqa: E402
from boi import rank as rank_mod  # noqa: E402

TABLES = ROOT / "app" / "data" / "tables.json"
RUNNER = ROOT / "tests" / "conformance.mjs"
SAMPLE = 1500
REAL_SAMPLE = 3000
SEED = 7

pytestmark = pytest.mark.skipif(shutil.which("node") is None,
                                reason="node is needed to run the browser pipeline")


def python_reading(word, limit=3, phones=None):
    """generate.candidates without the lexicon, on the phones given.

    Without phones it takes the spelling path, which is what the browser does
    for a word outside the shards. With them it takes whatever it is handed,
    which is how the real CMUdict stress patterns get compared.
    """
    if phones is None:
        phones = spell.phones(word)
    if phones is None:
        return None, []
    import itertools

    scored = {}
    hints = spell.align_vowels(word, phones)
    for slots, structural in syllabify.variants(phones, hints):
        options = [generate._slot_options(s) for s in slots]
        if not all(options):
            continue
        floor = sum(o[0][1] for o in options)
        for combo in itertools.product(*options):
            penalty = sum(p for _, p in combo)
            if penalty > floor + generate.BUDGET:
                continue
            syls = [s._replace(tone=tone.tone_of(slot, s))
                    for slot, (s, _) in zip(slots, combo)]
            text = vi.render_word(syls)
            total = rank_mod.score(syls, penalty, structural)
            if text not in scored or total < scored[text]:
                scored[text] = total
    ranked = [t for t, _ in sorted(scored.items(), key=lambda kv: (kv[1], kv[0]))]
    return phones, ranked[:limit]


def sample_words():
    """Real vocabulary, brand-shaped coinages, and random letter strings."""
    import cmudict

    rng = random.Random(SEED)
    real = sorted(w for w in cmudict.dict() if w.isalpha() and 2 <= len(w) <= 14)
    words = rng.sample(real, SAMPLE)
    words += ["logitech", "lazada", "zalopay", "vinfast", "momo", "shopee",
              "grabfood", "techcombank", "baemin", "gojek", "canva", "figma",
              "hmm", "shh", "zzz", "brrr", "qwerty", "xyzzy",
              # compounds, which exercise splitInto
              "poweroff", "blackpink", "airpod", "facetime", "skincare",
              "screensaver", "keyboardwarrior", "icecream", "sunflower"]
    for _ in range(300):
        n = rng.randint(2, 11)
        words.append("".join(rng.choice(string.ascii_lowercase) for _ in range(n)))
    return sorted(set(words))


def real_pairs():
    """CMUdict words with the phones the pipeline actually uses for them.

    The eval and every word pinned in test_pipeline go in first, since those
    are the ones whose rules were written against real phones; then a seeded
    sample of the rest.
    """
    import csv
    import cmudict

    words = set()
    for split in ("dev", "test"):
        with open(ROOT / "data" / "splits" / f"{split}.csv", encoding="utf-8") as f:
            words |= {r["word"] for r in csv.DictReader(f)}
    words |= {"improvement", "development", "temperature", "template", "accurate",
              "english", "schedule", "module", "education", "conscious",
              "delicious", "enthusiasm", "algorithm", "album", "these",
              "chinese", "family", "mechanical", "singing", "singer", "camera",
              "teacher", "order", "lifetime", "bus", "love", "crush", "netflix"}
    real = sorted(w for w in cmudict.dict() if w.isalpha() and 3 <= len(w) <= 14)
    words |= set(random.Random(SEED + 1).sample(real, REAL_SAMPLE))
    return [(w, g2p.phones(w)) for w in sorted(words) if g2p.phones(w)]


def acronym_tokens():
    """Cased input, since the acronym rules are the only ones that read case."""
    rng = random.Random(SEED + 2)
    upper, lower = string.ascii_uppercase, string.ascii_lowercase
    words = ["USB", "IT", "OK", "NASA", "RAM", "GIF", "IOS", "GPS", "HTTPS", "UNESCO",
             "ChatGPT", "iOS", "macOS", "eSIM", "iPhone", "MP3", "4G", "B2B", "A380",
             "COVID19", "HTML5", "2024", "A", "usb", "mp3", "Chat", "ChatGPT4"]
    for _ in range(300):
        caps = "".join(rng.choice(upper) for _ in range(rng.randint(2, 6)))
        words += [caps, caps + str(rng.randint(0, 99)),
                  str(rng.randint(0, 9)) + caps,
                  "".join(rng.choice(lower) for _ in range(rng.randint(1, 5))) + caps]
    return sorted(set(words))


def test_browser_pipeline_matches_python():
    assert TABLES.exists(), "run: uv run scripts/build_tables.py"
    words = sample_words()
    pairs = real_pairs()
    import cmudict

    known = sorted(w for w in cmudict.dict() if w.isalpha() and len(w) >= 3)
    payload = {"tables": json.loads(TABLES.read_text(encoding="utf-8")),
               "words": words, "known": known, "pairs": pairs,
               "acronyms": acronym_tokens()}

    done = subprocess.run(
        ["node", str(RUNNER)],
        input=json.dumps(payload), capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stderr[-2000:]
    out = json.loads(done.stdout)
    js, real = out["spelled"], out["real"]

    mismatches = []
    for word in payload["acronyms"]:
        want = letters.acronym_parts(word, g2p.ordinary_word)
        want = [list(p) for p in want] if want else None
        if out["acronyms"][word] != want:
            mismatches.append(f"{word} acronym\n  py {want}\n  js {out['acronyms'][word]}")
    for word, phones in pairs:
        want = python_reading(word, phones=phones)[1]
        got = real[word]["readings"]
        if got != want:
            mismatches.append(f"{word} {' '.join(phones)}\n  py {want}\n  js {got}")
        if real[word]["letters"] != spell.align_vowels(word, phones):
            mismatches.append(f"{word} letters\n  py {spell.align_vowels(word, phones)}"
                              f"\n  js {real[word]['letters']}")
        if len(mismatches) >= 8:
            break
    for word in words:
        phones, readings = python_reading(word)
        got = js[word]
        if (got["phones"] or None) != phones or got["readings"] != readings:
            mismatches.append(
                f"{word}\n  py {phones} {readings}\n  js {got['phones']} {got['readings']}")
        if got["letters"] != letters.read(word):
            mismatches.append(
                f"{word} letters\n  py {letters.read(word)}\n  js {got['letters']}")
        if got["split"] != g2p._split(word):
            mismatches.append(
                f"{word} split\n  py {g2p._split(word)}\n  js {got['split']}")
        if len(mismatches) >= 8:
            break

    assert not mismatches, (
        f"{len(mismatches)}+ disagreements between the Python pipeline and "
        f"app/scripts/oov.js, over {len(pairs)} words on their real phones and "
        f"{len(words)} on the spelling path:\n\n" + "\n\n".join(mismatches))
