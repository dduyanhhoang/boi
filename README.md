# Boi

Turns an English word into how Vietnamese speakers actually read it, written as
Vietnamese syllables with tones. The name comes from "tiếng Anh bồi", the
nativized English you hear in everyday Vietnamese speech.

```
$ uv run boi information schedule context software
information	in phơ mây sừn
schedule	sờ ke giu
context	con tếch
software	sóp goe
```

The target is nativization. `in phô mây sừn` is the right answer for
*information* even though `in phọc mây sần` keeps more of the English sounds,
because the first is what people say. Every syllable the generator emits is a
pronounceable Vietnamese one: the rhyme table in `src/boi/vi.py` filters out
the rest, which is why *context* comes out `con tếch` and not `con téc`.

Dialect is Northern and colloquial. Pronunciations come from CMUdict, so the
English side is American.

## Install and use

Needs [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run boi website laptop wifi
uv run boi --all database          # the ranked alternatives
```

`uv sync --extra oov` adds `g2p_en`, which predicts phones for a word CMUdict
does not have. Without it an unknown word returns nothing rather than a guess.

## How well it works

181 hand-written readings, all reviewed by a native speaker, split 131 dev and
50 test. Rules were written against dev only; test was scored once.

| | dev | test |
|---|---|---|
| exact match on `vi_form` | 0.718 | 0.540 |
| match on `vi_form` or an `alt_form` | 0.740 | 0.620 |
| gold form in the top 5 | 0.832 | 0.760 |
| syllable error rate | 0.181 | 0.273 |
| tone accuracy | 0.956 | 0.933 |

The gap between dev and test is hand-tuning on 131 words. Tone is the strongest
part, because four rules cover almost all of it: an inserted vowel takes huyền,
a stop coda takes sắc, a final `-tion` or `-le` takes huyền, everything else
is ngang.

The weakest tags on dev are `coda_l` (6 of 13), where a final l can become a u
glide, an o glide, an n or nothing, and the multi-syllable stress tags, where
the gold reduces vowels in ways the phone string does not predict. `taxi` wants
`tắc xi` and gets `tách si`; `report` wants `rì pọt` and gets `ri pọt`.

Reproduce:

```sh
uv run eval/run_eval.py dev --errors --tags
uv run eval/run_eval.py test
```

## How it works

```
src/boi/vi.py          quốc ngữ <-> syllable slots, and the rhyme inventory
src/boi/g2p.py         word -> ARPAbet (CMUdict, g2p_en fallback)
src/boi/phonemap.py    ARPAbet -> Vietnamese slot options, each with a penalty
src/boi/syllabify.py   phones -> syllable slots: cluster repair, gemination
src/boi/tone.py        tone per syllable
src/boi/rank.py        candidate scoring
src/boi/align.py       gold alignment, used to check phonemap
src/boi/generate.py    end to end, and the CLI
```

A word becomes phones, the phones become one or more syllable layouts, each
slot in a layout offers a few Vietnamese pieces, and the combinations are
ranked by the penalties that produced them. Illegal rhymes are dropped before
ranking. Nothing is learned end to end, so every output traces back to a named
rule or a table row.

Two parts of `boi.md` are deliberately absent, with reasons in `rank.py`: the
panphon feature-distance filter and a corpus-counted syllable-frequency prior.
`src/boi/rhymes.py`, counted from dev by `scripts/build_rhymes.py`, stands in
for the second one.

One rule from `boi.md` is contradicted by the data and left out. An unstressed
syllable before the stressed one is supposed to take huyền; that fits `rì pọt`
and `đì dai` and breaks `sô lu sừn`, `hê lô`, `ba na na`, `con tờ rôn` and
`i ven`. The note stays in `tone.py` next to the disabled rule.

## Data and scripts

```sh
uv run scripts/build_eval.py        # rebuild data/eval_v0.csv from its ROWS block
uv run scripts/make_splits.py       # rebuild the dev and test splits
uv run scripts/build_rhymes.py      # recount src/boi/rhymes.py from dev
uv run scripts/report_coverage.py   # aligned phone -> Vietnamese counts
uv run pytest                       # 464 checks, including the orthography round trip
```

`data/eval_v0.csv` has 181 rows: `word`, `arpabet`, `vi_form`, `alt_forms`,
`vi_native` (the Vietnamese word for the thing, where one exists), `tags`,
`confidence` and `status`. 133 readings were approved as written and 48 were
corrected by the reviewer.

The splits are stratified so every tag appears in both halves. Thirteen tags
occur once in the whole set and cannot be split; those rows are in dev.

To grow the set, run the generator over a word list and give the sheet to a
speaker to correct:

```sh
printf 'router\nbrunch\n' | uv run scripts/make_review_sheet.py -
```

The sheet's columns match the eval set, so corrected rows concatenate onto it.

`boi.md` is the design brief: prior work, the linguistic findings behind the
tables, and the open questions.
