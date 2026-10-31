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

Any word works. CMUdict covers 117,496 of them; anything else is read off its
spelling, which is what a Vietnamese speaker does with unfamiliar written
English: `logitech` becomes lo-gi-tech becomes `lô di tếch`. `uv sync --extra
oov` adds `g2p_en`, which predicts phones more accurately than the spelling
rules and is tried first when it is installed.

## How well it works

181 hand-written readings, all reviewed by a native speaker, split 131 dev and
50 test. Rules were written against dev only; test was scored once.

| | dev, rules only | dev, with lexicon | test |
|---|---|---|---|
| exact match on `vi_form` | 0.725 | 0.756 | 0.540 |
| match on `vi_form` or an `alt_form` | 0.740 | 0.771 | 0.620 |
| gold form in the top 5 | 0.832 | 0.840 | 0.760 |
| syllable error rate | 0.174 | 0.158 | 0.273 |
| tone accuracy | 0.956 | 0.956 | 0.933 |

All four lexicon words are dev rows, so the lexicon column is partly
memorisation and the rules-only column is the one to compare against test.

The gap between dev and test is hand-tuning on 131 words. Tone is the strongest
part, because four rules cover almost all of it: an inserted vowel takes huyền,
a stop coda takes sắc, a final `-tion` or `-le` takes huyền, everything else
is ngang.

The weakest tags on dev are `coda_l` (6 of 13), where a final l can become a u
glide, an o glide, an n or nothing, and the multi-syllable stress tags, where
the gold reduces vowels in ways the phone string does not predict. `taxi` wants
`tắc xi` and gets `tách si`; `report` wants `rì pọt` and gets `ri pọt`; `cool`
wants `cu` and gets `cun`, because `school` is `sờ cun` on the same vowel and
the same stress and no rule tells the two apart.

There is a second, outside measure. `data/ngo/` holds 2,400 English words with
Vietnamese readings from [Ngo et al.](https://arxiv.org/abs/1810.03184) (MIT),
produced for a different purpose by people who never saw this project. They
are names, which people meet in writing, and the verdict there is the opposite
way round:

| | spoken loanwords (181) | written names (2,394) |
|---|---|---|
| heard reading, from CMUdict | **0.707** | 0.125 |
| letter reading | 0.420 | **0.211** |

Two independent sets, each preferring a different reading, which is the case
for keeping both. It also gives `letters.py` a measurement it otherwise has
none of. Nothing is fitted on the Ngo data; `--split dev` holds half back.

Their code is in the repo too, and it runs, so the comparison goes both ways.
`third_party/ngo/` holds it (MIT, fifteen `print` statements converted to
Python 3 and nothing else), and `scripts/build_web_data.py` runs it over every
CMUdict word so the playground can show their reading for anything, not only
the 2,400 they published.

Each system wins on the task it was built for, by a wide margin both times:

| | their 2,391 names | our 181 loanwords |
|---|---|---|
| Ngo et al.'s system | **0.354** | 0.213 |
| this, heard | 0.125 | **0.742** |
| this, letters | 0.213 | 0.265 |

Theirs is name transliteration for ASR; this is everyday loanwords as written
bồi. Neither number is a target for the other.

One caveat the page carries too. Their input is one phone symbol per letter,
and their own lexicon had pronunciations CMUdict does not list, so for words
outside their 2,400 the input is rebuilt here from CMUdict by an aligner that
reproduces their own alignment on 82% of held-out words. Those readings are
labelled "rebuilt"; the 2,391 published ones are not.

Reproduce:

```sh
uv run eval/run_eval.py dev --errors --tags
uv run eval/run_eval.py test
uv run eval/run_ngo.py --reading letters --split dev
```

## Playground

`app/` is a static page that looks up precomputed readings: type a word, see the
reading, the syllables with their tones, the phones it started from, and, for
the 181 reviewed words, what the native speaker wrote.

```sh
uv run scripts/build_web_data.py          # writes app/data, not committed
python3 -m http.server --directory app    # then open localhost:8000
```

GitHub Actions rebuilds `app/data` and deploys `app/` to Pages on every push
that touches the rules or the page, so the published readings always match the
rules in `src/boi` at that commit.

A word the shards do not have is worked out in the browser by
`app/scripts/oov.js`, which reruns the pipeline there. Its tables are generated
from the Python modules by `scripts/build_tables.py`, so only the control flow
exists twice, and `tests/test_js_conformance.py` runs both over 1,800 words and
fails the build on any disagreement.

Design follows the owner's UIUX spec, recorded with its resolved token values
in `docs/DESIGN.md`.

## Two readings

A speaker who has heard a word says it the way they heard it; a speaker
meeting it in writing sounds the letters out with Vietnamese values. Both are
real, and no rule tells which applies, so both are available.

```sh
uv run boi ecology            # i ca la di      the heard reading, the default
uv run boi --read ecology     # ê cô lô gi      the letters, read as Vietnamese
uv run boi --all ecology      # both, with alternatives
```

The page shows both: the heard reading large, the letter reading on a line
under it, and clicking it makes it the main reading. For the 2,391 words Ngo
et al. cover, their reading sits on that line too, so three systems can be
compared at a glance. Where their notation cannot separate two spellings, a
reading that differs only there counts as agreement and the line says so
rather than repeating it.

The default is the heard reading because the data says so: over the 181
reviewed rows it matches 0.707 against 0.420 for the letters, winning 54 words
and losing 2. The letter reading is better for words people meet in writing
(`ecology`, `medicine`) and worse for the loanwords people say (`information`,
`software`, `google`), which is what the reviewed set is made of.

## How it works

```
src/boi/vi.py          quốc ngữ <-> syllable slots, and the rhyme inventory
src/boi/g2p.py         word -> ARPAbet (CMUdict, then g2p_en, then spelling)
src/boi/spell.py       spelling -> ARPAbet, for words CMUdict lacks
src/boi/letters.py     spelling -> Vietnamese directly, the second reading
src/boi/phonemap.py    ARPAbet -> Vietnamese slot options, each with a penalty
src/boi/syllabify.py   phones -> syllable slots: cluster repair, gemination
src/boi/tone.py        tone per syllable
src/boi/rank.py        candidate scoring
src/boi/lexicon.py     the four words no rule predicts
src/boi/align.py       gold alignment, used to check phonemap
src/boi/generate.py    end to end, and the CLI

app/                   the playground: markup, tokens, stylesheet, scripts
docs/brief.md          the design brief
docs/PRODUCT.md        what the product is and who it is for
docs/DESIGN.md         resolved design tokens and the decisions behind them
```

A word becomes phones, the phones become one or more syllable layouts, each
slot in a layout offers a few Vietnamese pieces, and the combinations are
ranked by the penalties that produced them.

CMUdict is right about some vowels and loses the rest. It reduces an
unstressed vowel to a schwa, which throws away which letter it was, so
refrigerator read as `ra phờ ri` where a Vietnamese reader says `rê`. So the
word's vowel letters are lined up against its vowel phones, which works for
175 of the 181 gold rows, and the letter is used where it is the better
evidence:

- a reduced vowel in an open syllable takes its letter's value
- so does one before a coda n, which is how development gets `lắp men`
- /ɪ/ and /i/ written with one plain letter take that letter's value when the
  syllable is stressed or closed, which is how encyclopedia gets `en` and `pê`
- `er` is `ơ` but `or` inside a word is `ô`, so information is `in phô mây sừn`
- `-tion` is one piece wherever it sits, not only at the end of a word, so
  international is `in tơ nát sừn nồ`

and CMUdict keeps the rest. A digraph is an English spelling convention a
Vietnamese reader does not apply, so `free` stays `phờ ri` and `team` stays
`tim`. A word-initial open vowel is a prefix read as the English letter name,
so `email` is `i meo` and `esport` is `i sờ pọt`. Illegal rhymes are dropped before
ranking. Nothing is learned end to end, so every output traces back to a named
rule or a table row.

Two parts of `docs/brief.md` are deliberately absent, with reasons in `rank.py`: the
panphon feature-distance filter and a corpus-counted syllable-frequency prior.
`src/boi/rhymes.py`, counted from dev by `scripts/build_rhymes.py`, stands in
for the second one.

`lexicon.py` holds four words: `shop` and `sauce` take x where `sóp pinh` and
`sót` take s, `mall` is the one final l that drops rather than glides, and
`bus` is `bớt` where the same vowel gives `bắc` and `ắp`. `docs/brief.md` predicts
each of them as lexical. The rule-based form is still generated and still
shows up under `--all`.

One rule from `docs/brief.md` is contradicted by the data and left out. An unstressed
syllable before the stressed one is supposed to take huyền; that fits `rì pọt`
and `đì dai` and breaks `sô lu sừn`, `hê lô`, `ba na na`, `con tờ rôn` and
`i ven`. The note stays in `tone.py` next to the disabled rule.

## Data and scripts

```sh
uv run scripts/build_eval.py        # rebuild data/eval_v0.csv from its ROWS block
uv run scripts/make_splits.py       # rebuild the dev and test splits
uv run scripts/build_rhymes.py      # recount src/boi/rhymes.py from dev
uv run scripts/report_coverage.py   # aligned phone -> Vietnamese counts
uv run pytest                       # 466 checks, including the orthography round trip
```

`data/eval_v0.csv` has 181 rows: `word`, `arpabet`, `vi_form`, `alt_forms`,
`vi_native` (the Vietnamese word for the thing, where one exists), `tags`,
`confidence` and `status`. 132 readings were approved as written and 49 were
corrected by the reviewer.

The splits are stratified so every tag appears in both halves. Thirteen tags
occur once in the whole set and cannot be split; those rows are in dev.

## Growing the eval

181 words is not enough. They are all short spoken loanwords, so a rule that
is wrong for long Latinate words, brands or compounds can pass every check
here, which is how wrong readings keep surfacing one at a time.

`data/review/sheet_001.csv` is the next round: 251 words covering the classes
the first set misses, grouped by tag so similar words sit together.

Review it at [/review](https://dduyanhhoang.github.io/boi/review/) rather than
in the CSV: one word at a time, the generator's candidates as buttons, 1 to 5
to pick, Enter for the first, S to skip, and a field for anything else.
Progress is kept in the browser, so it can be done in sittings. Export writes
the sheet back out.

Editing the CSV by hand works too: change `vi_form` where the reading is
wrong, leave it where it is right, and set `status` to `approved` or
`corrected`. Rows left as `generated` count as unreviewed either way.

```sh
uv run scripts/merge_review.py data/review/sheet_001.csv --dry-run
uv run scripts/merge_review.py data/review/sheet_001.csv
uv run scripts/build_eval.py && uv run scripts/make_splits.py \
  && uv run scripts/build_rhymes.py
```

Every reading is parsed before it is accepted, so a typo is caught at merge
time rather than breaking the orthography round trip later.

To build a different sheet:

```sh
uv run scripts/make_review_sheet.py data/growth_words.txt > sheet.csv
```

`docs/brief.md` is the design brief: prior work, the linguistic findings behind the
tables, and the open questions.
