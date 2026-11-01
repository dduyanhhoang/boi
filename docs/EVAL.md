# Evaluation

## The set

181 readings of English words, each reviewed by a native speaker: 132 approved as written, 49 corrected. They are split 131 for development and 50 for testing, stratified so every tag appears in both halves. Thirteen tags occur once in the whole set and sit in the development half. Rules are written against development only.

| | dev | test |
|---|---|---|
| exact match | 0.878 | 0.780 |
| exact, rules alone | 0.847 | 0.760 |
| any accepted form | 0.893 | 0.860 |
| gold form in the top 5 | 0.931 | 0.880 |
| syllable error rate | 0.071 | 0.100 |
| tone accuracy | 0.980 | 0.972 |

Five of the 181 are lexicon entries, memorised rather than derived: `mall`, `sauce`, `shop` and `taxi` in development, `system` in test. Read the "rules alone" row to compare against anything new; `run_eval.py` prints it beside every figure and names the entries.

## The test half is not fully held out

Seven test rows were looked at while rules were being written: `database`, `singer`, `snow`, `hello`, `video`, `deadline` and `livestream`. An early version of `scripts/mine_rules.py` read the whole set rather than the development half, and two later error hunts did the same. Over the 43 test rows never looked at, the rules alone score **0.744**. That is the honest held-out figure. The miner now reads `data/splits/dev.csv` and takes `--split` to say otherwise.

## Two readings

A speaker who has heard a word says it as they heard it. A speaker meeting it in writing sounds out the letters with Vietnamese values. Both happen, so both are available, and the data says which to lead with.

| | spoken loanwords (181) | written names (2,391) |
|---|---|---|
| heard reading, from the phones | **0.856** | 0.121 |
| letter reading | 0.254 | **0.213** |

The loanwords are what people say, so the heard reading wins there and is the default. The names come from [Ngo et al. 2014](https://github.com/ngohgia/transliteration) (MIT), made for a different purpose by people who never saw this project; people meet names in writing, so there the letters win. Nothing is fitted on the Ngo data.

Their repository ships their own system's output for the same 2,391 names. It agrees with their reference 0.354 of the time, against 0.262 for this project taking either reading. Their system was built for names and this one was not.

Their code is vendored in `third_party/ngo/` and runs, but this project's Python 3 port does not reproduce their results: on their own input it matches their shipped output 28.4% of the time. Nothing is generated from it. `src/boi/ngo_model.py` is their method written from [the 2018 paper](https://arxiv.org/abs/1810.03184) instead, pinned to the paper's own worked example in `tests/test_ngo_model.py`.

## Data and scripts

```sh
uv run scripts/build_eval.py        # rebuild data/eval_v0.csv from its ROWS block
uv run scripts/make_splits.py       # rebuild the dev and test splits
uv run scripts/build_rhymes.py      # recount src/boi/rhymes.py from dev
uv run scripts/mine_rules.py        # contexts where dev agrees and the rules do not
uv run scripts/check_robustness.py  # whether a misspelling reads like the word
uv run pytest                       # 661 tests
```

`data/eval_v0.csv` has one row per word: `word`, `arpabet`, `vi_form`, `alt_forms`, `vi_native` (the Vietnamese word for the thing, where one exists), `tags`, `confidence` and `status`. Change a reading in `scripts/build_eval.py`, which generates the CSV, not in the CSV itself.

## Growing the eval

181 short spoken loanwords is not enough. A rule that is wrong for long Latinate words, brands or compounds can pass every check here, which is why wrong readings keep surfacing one at a time.

`data/review/sheet_001.csv` is the next round: 251 words covering the classes the first set misses. Review it at [/review](https://dduyanhhoang.github.io/boi/review/), one word at a time with the generator's candidates as buttons: 1 to 5 to pick, Enter for the first, S to skip, and a field for anything else. Progress is kept in the browser, so it can be done in sittings, and Export writes the sheet back out.

```sh
uv run scripts/merge_review.py data/review/sheet_001.csv --dry-run
uv run scripts/merge_review.py data/review/sheet_001.csv
uv run scripts/build_eval.py && uv run scripts/make_splits.py && uv run scripts/build_rhymes.py
```

Every reading is parsed before it is accepted, so a typo is caught at merge time.
