# Boi

Turns an English word into how Vietnamese speakers actually read it, written as
Vietnamese syllables with tones. The name comes from "tiếng Anh bồi", the
nativized English you hear in everyday Vietnamese speech.

```
information  ->  in phô mây sừn
schedule     ->  sờ ke đùa
context      ->  con tếch
```

The target is nativization. `in phô mây sừn` is the right answer for
*information* even though `in phọc mây sần` keeps more of the English sounds,
because the first is what people say. Every output piece is a legal Vietnamese
syllable.

Dialect is Northern and colloquial. Pronunciations come from CMUdict, so the
English side is American.

## Status

The eval set is done: 181 words (tech, office, social media, food, everyday
vocabulary, colours, brands), each reviewed by a native speaker. 133 readings
stood as written, 48 were corrected. It lives in `data/eval_v0.csv` and
`scripts/build_eval.py` rebuilds it from the `ROWS` block inside that script.

The pipeline itself is not written yet. `boi.md` has the design: alignment
table, syllabification into Vietnamese slots, tone assignment from English
stress, orthography, candidate ranking, and the evaluation plan.

## Install and run

Needs [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run scripts/build_eval.py   # rewrites data/eval_v0.csv
uv run pytest
```

## Layout

```
data/eval_v0.csv        gold readings, with ARPAbet and sound tags
data/splits/            dev and test splits (not built yet)
src/boi/g2p.py          word -> ARPAbet
scripts/build_eval.py   rebuilds the eval CSV
tests/                  checks the CSV stays reproducible
boi.md                  design brief, prior work, open questions
```

## Design constraints

CPU only, few dependencies, rule-based core. Small learned parts are allowed
where rules cannot decide, and a small G2P model such as `g2p_en` is allowed
only for words missing from CMUdict. Rules and tables stay readable so a wrong
output can be traced to one rule.
