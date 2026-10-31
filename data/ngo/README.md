# Ngo et al. transliteration data

`large_test.lex` and `large_test.vie` are vendored from
[ngohgia/transliteration](https://github.com/ngohgia/transliteration) (MIT),
the code for Ngo, Sim, Chng and Li, *A Phonology-Augmented Statistical
Framework for Machine Transliteration using Limited Linguistic Resources*,
IEEE/ACM TASLP 2018 ([arXiv:1810.03184](https://arxiv.org/abs/1810.03184)).

2,400 English words with Vietnamese readings, written in X-SAMPA with tone
numbers. Mostly proper names, which is a different task from this one, but on
the five words it shares with `data/eval_v0.csv` its readings match the gold
four times out of five, so it is a useful second opinion from a source that
never saw this project.

`eval/run_ngo.py` decodes the X-SAMPA and scores against it. Nothing here is
fitted on this data; it is held out entirely.
