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

from boi import g2p, generate, spell, syllabify, tone, vi  # noqa: E402
from boi import rank as rank_mod  # noqa: E402

TABLES = ROOT / "app" / "data" / "tables.json"
RUNNER = ROOT / "tests" / "conformance.mjs"
SAMPLE = 1500
SEED = 7

pytestmark = pytest.mark.skipif(shutil.which("node") is None,
                                reason="node is needed to run the browser pipeline")


def python_reading(word, limit=3):
    """generate.candidates, but forced down the spelling path."""
    phones = spell.phones(word)
    if phones is None:
        return None, []
    import itertools

    scored = {}
    for slots, structural in syllabify.variants(phones):
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


def test_browser_pipeline_matches_python():
    assert TABLES.exists(), "run: uv run scripts/build_tables.py"
    words = sample_words()
    import cmudict

    known = sorted(w for w in cmudict.dict() if w.isalpha() and len(w) >= 3)
    payload = {"tables": json.loads(TABLES.read_text(encoding="utf-8")),
               "words": words, "known": known}

    done = subprocess.run(
        ["node", str(RUNNER)],
        input=json.dumps(payload), capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stderr[-2000:]
    js = json.loads(done.stdout)

    mismatches = []
    for word in words:
        phones, readings = python_reading(word)
        got = js[word]
        if (got["phones"] or None) != phones or got["readings"] != readings:
            mismatches.append(
                f"{word}\n  py {phones} {readings}\n  js {got['phones']} {got['readings']}")
        if got["split"] != g2p._split(word):
            mismatches.append(
                f"{word} split\n  py {g2p._split(word)}\n  js {got['split']}")
        if len(mismatches) >= 8:
            break

    assert not mismatches, (
        f"{len(mismatches)}+ of {len(words)} words differ between the Python "
        f"pipeline and app/scripts/oov.js:\n\n" + "\n\n".join(mismatches))
