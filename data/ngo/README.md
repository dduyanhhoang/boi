# Ngo et al. transliteration data

Vendored from [ngohgia/transliteration](https://github.com/ngohgia/transliteration)
(MIT), from its `symbolic_transliterators/vietnamese/` directory. That is the
work of Ngo, Chen, Sivadas, Ma and Li, *A Minimal-Resource Transliteration
Framework for Vietnamese*, Interspeech 2014.

Note the citation: an earlier version of this file pointed at
[arXiv:1810.03184](https://arxiv.org/abs/1810.03184), the 2018 TASLP paper on
their phonology-augmented *statistical* framework. That is a different system,
living in a different directory of their repo. These files belong to the 2014
symbolic one.

2,400 English words with Vietnamese readings, written in X-SAMPA with tone
numbers. Mostly proper names, which is a different task from this one, but on
the five words it shares with `data/eval_v0.csv` its readings match the gold
four times out of five, so it is a useful second opinion from a source that
never saw this project.

Three files: `large_test.lex` is the input, English words with English
phones; `large_test.vie` is the Vietnamese reference; `large_test.output` is
their own system's prediction. The last two agree 35% of the time, which is
how you can tell which is which.

`eval/run_ngo.py` decodes the X-SAMPA and scores against the reference, and
`--baseline` scores their system the same way, so the comparison is like for
like. Nothing here is fitted on; `--split` holds half back.

Their method and this one converge and diverge in a way worth knowing. Their
first stage builds "pseudo-syllables", assigning source graphemes to
onset/nucleus/coda slots under the target language's phonotactics, which is
what `syllabify.py` and `vi.LEGAL_CODAS` do, arrived at separately. Their
mapping is conditioned on which slot a grapheme landed in, their example
being l to /n/ in a coda and /l/ in an onset, which is what the split between
`phonemap.ONSET` and `phonemap.CODA` encodes.

Where they differ is the axis this project keeps running into: they map
source graphemes straight to target phonemes and deliberately skip the source
pronunciation, to avoid importing source-language assumptions. This project
reaches for CMUdict first and the letters second. `letters.py` is the closer
match to their architecture, and it is the one that scores better on their
data.
