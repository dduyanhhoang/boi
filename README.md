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
| exact match on `vi_form` | 0.847 | 0.878 | 0.780 |
| match on `vi_form` or an `alt_form` | 0.832 | 0.870 | 0.860 |
| gold form in the top 5 | 0.893 | 0.908 | 0.880 |
| syllable error rate | 0.119 | 0.095 | 0.100 |

Two test rows are lexicon entries, `schedule` and `system`, so **0.740** is
the figure to read for the test column: that is what the rules alone get, and
`run_eval.py` prints it beside every number and names the entries.

The test column is not clean. `scripts/mine_rules.py` read the whole of
`eval_v0.csv` rather than the dev split when it was written, and a later
error hunt did the same, so five test rows were looked at and used:
`database`, `singer`, `snow`, `hello`, `video`, `deadline` and `livestream`.
Six of the seven are now hits. Over the 43 never looked at it is **0.698**,
and that is the one to compare against anything new. The miner now reads
`data/splits/dev.csv` and takes `--split` to say otherwise.
| tone accuracy | 0.956 | 0.956 | 0.942 |

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
Vietnamese readings from [Ngo et al. 2014](https://github.com/ngohgia/transliteration)
(MIT), produced for a different purpose by people who never saw this project. They
are names, which people meet in writing, and the verdict there is the opposite
way round:

| | spoken loanwords (181) | written names (2,394) |
|---|---|---|
| heard reading, from CMUdict | **0.707** | 0.125 |
| letter reading | 0.420 | **0.211** |

Two independent sets, each preferring a different reading, which is the case
for keeping both. It also gives `letters.py` a measurement it otherwise has
none of. Nothing is fitted on the Ngo data; `--split dev` holds half back.

Their repo also ships their own system's output for those words, so the
comparison is like for like on the same 2,391:

| | agreement with their reference |
|---|---|
| Ngo et al.'s system | **0.354** |
| this, either reading | 0.269 |
| this, letters | 0.213 |
| this, heard | 0.125 |

Their system was built for that task and this one was not, so the gap is the
expected shape rather than a verdict.

Their code is vendored in `third_party/ngo/` and it runs, but **this project's
Python 3 port of it does not reproduce their results**: on their own input it
matches their own shipped output 28.4% of the time, and on the example in
their paper, disneyland, the paper gives `đi sờ ni len` where that copy gives
`đi ni lan`. Nothing is generated from it.

`src/boi/ngo_model.py` is their method instead, written from
[the 2018 paper](https://arxiv.org/abs/1810.03184) rather than ported: the
pseudo-syllable formulation of Section III-A, the grapheme-to-phoneme mapping
of Eq. 8, and the tone model of Eq. 9. It is pinned to the paper's own worked
example, Figure 4, which formulates DISNEYLAND as D-I / S-@: / N-EY / L-A-N;
`tests/test_ngo_model.py` checks the derived labels against that figure
exactly.

Trained on the 2,273 of their 2,400 pairs that yield ground-truth labels, it
reaches 0.924 label accuracy, 0.927 tone accuracy and 0.288 whole-word
accuracy on a held-out fifth, against 0.354 for their own system on the same
reference. It needs no GPU and no training run: all three models are counts,
fitted in about a second.

The whole-word figure was 0.295 until the tone model was fixed, and the drop
is the measurement becoming real rather than the model getting worse.
`target_slots` drops every `_`-prefixed token, tones among them, and
`slots_to_syllables` was filling in `_1` for all of them, so Eq. 9 was
trained on a constant: 15,945 ngang and nothing else. Both the prediction and
the gold it was scored against were ngang throughout, which made tone free.
With the tones read back, `disneyland` gives `đi sờ nây lan`, matching the
paper's own `sờ`.

What still differs from Figure 4 is the training corpus, not the method. They
published `large_test.lex`, their *test* set: 2,400 foreign proper names. The
lexicon they trained on is not in the repo, so every mapping is counted from
names. The key `(N, ey, IY)` never occurs there, and `(N, a, AE)` reads `a:`
378 times against `E` 5. Their own reference even gives `ney` as `n @I` and
`bailey` as `b_< a:I . l @I`, so Figure 4's `n i` disagrees with the data
they shipped alongside it.

The playground shows it as "their method, reimplemented", kept distinct from
the 2,391 readings they published, which stay labelled as theirs.

`scripts/mine_rules.py` is how the last few rules were found rather than
guessed. It aligns every gold reading to the slots that produced it and
reports any context where the gold agrees with itself across two or more rows
and this generator disagrees with it. Run against all three slots it is
currently empty, so what is left is either lexical or a context the gold
itself splits on.

`scripts/check_robustness.py` measures something the eval cannot: every row
in the eval is spelled correctly, so none of it says what happens when a
reader mistypes. It doubles letters the way people do and asks whether the
reading survives.

| | misspellings reading as the word does |
|---|---|
| before | 0.207 |
| after `g2p.undoubled` | **0.962** |

What is left is mostly right: `mousse`, `shoop`, `buus` and `hottel` are all
words CMUdict lists in their own right, so reading them as themselves is the
answer. `livestream` is not in CMUdict at all, so its variants go through
compound splitting and land on different splits.

Reproduce:

```sh
uv run scripts/mine_rules.py --slot nucleus
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
