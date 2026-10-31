# Ngo et al.'s symbolic transliterator, vendored

The Vietnamese symbolic transliterator from
[ngohgia/transliteration](https://github.com/ngohgia/transliteration) (MIT),
for Ngo, Chen, Sivadas, Ma and Li, *A Minimal-Resource Transliteration
Framework for Vietnamese*, Interspeech 2014.

Copied as-is apart from one change: fifteen Python 2 `print` statements are
now `print()` calls, so it runs under Python 3. No logic was touched.

It takes `word<TAB><TAB>phones`, one phone symbol per letter, `_` for a letter
with no sound, in a stress-free ARPAbet with allophones (AX, AXR, IX, DX, and
TD/DD/KD/PD/BD/GD for unreleased stops). It writes X-SAMPA with tone numbers.

    python3 transliterator.py input.lex output.txt

`scripts/build_ngo_readings.py` builds that input for every CMUdict word and
runs this, so the playground can show their reading beside ours. Their
original lexicon had pronunciations for words CMUdict does not list, so the
input this project feeds it is reconstructed rather than theirs; the readings
shipped for the 2,391 words in `data/ngo/` are their real output and are
preferred where they exist.
