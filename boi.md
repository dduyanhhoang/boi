# Boi: pipeline brief for Claude Code

## Task

Build a lightweight generator that turns an English word into how Vietnamese speakers actually read it, written as Vietnamese syllables with tones ("tiếng Anh bồi" style).

Project name: **Boi** (from "bồi", written without diacritics). Use `boi` for the repo and Python package.

Examples:

- information → in phô mây sừn
- schedule → sờ ke đùa
- context → con tếch

The target is nativization, not transliteration. Every output piece must be a valid Vietnamese syllable, read the way Vietnamese speakers say it, even when a form closer to English exists. "in phô mây sừn" is the correct answer even though "in phọc mây sần" keeps more English sounds.

Dialect: Northern, colloquial. Pronunciation base: American English (CMUdict).

## Constraints

- CPU only, few dependencies. Rule-based core; small learned parts only where rules cannot decide.
- No large neural model in the main path. A small G2P model (e.g. `g2p_en`) is allowed only as a fallback for words missing from CMUdict.
- Rules and learned tables must stay readable, so errors can be traced to a specific rule.

## Prior work (survey done 2026-10-30)

No public tool targets this exact output. Closest existing work:

- **VietNormalizer** (`pip install vietnormalizer`, MIT, 2026). Dictionary of about 17K entries plus rule fallback, used as a TTS front-end. Output is formal and hyphenated (`server` → `xơ-vơ`, `computer` → `com-pu-tơ`), with odd rule output such as `configuration` → `con-phi-gu-raân`. No tone rules tied to English stress.
- **Ngo et al.** (Interspeech 2014, 2015; arXiv 1810.03184). Rule-based then statistical transliteration with Vietnamese syllable structure and tone assignment. Aimed at ASR and names; inactive since 2018. Code: github.com/ngohgia/transliteration.
- **NEWS 2018** shared task had an English→Vietnamese transliteration track, mostly proper names.
- **TSPC** (arXiv 2509.05983) and **Whisper cross-lingual phoneme recognition** (arXiv 2508.19270) map English to Vietnamese syllables internally for code-switching ASR.
- **simphone** (github.com/nguyenvulebinh/simphone). Phonetic similarity search using panphon feature-weighted edit distance. Vietnamese side is light; English side needs PyTorch, Charsiu byT5 and pynini. Use panphon directly instead of simphone's English path.

Gap: no open dataset of colloquial readings with tones, no tone rules derived from English stress, no evaluation of naturalness.

## Linguistic findings to use

- French loanwords in Vietnamese: most syllables get ngang; syllables ending in a plosive mostly get sắc (92% in that corpus).
- Vietnamese repairs clusters both by deleting a consonant and by inserting a vowel. Generate both and let ranking choose.
- Vietnamese listeners map English stress onto tones using relative F0.
- Mandarin loanword study: English onset voicing and stress-driven pitch predict tone. Use onset voicing as a tone feature.

## Eval set (done)

Files: `al_viet_eval_v0.csv` and `build_eval.py` (rebuilds the CSV from the `ROWS` block and fills ARPAbet from CMUdict).

- 181 words: tech, office, social media, food, everyday words, colours, brands.
- All rows reviewed by a native speaker: 133 `approved`, 48 `corrected`.
- Columns: `id`, `word`, `arpabet` (CMUdict, with stress), `vi_form` (main reading), `alt_forms` (`;`-separated), `tags` (`;`-separated sound features), `confidence` (h/m/l), `status`.
- livestream, icecream and tiktok are not in CMUdict; their ARPAbet is composed from parts in `MANUAL`.

Known cleanup: a few `alt_forms` hold Vietnamese translations rather than readings (speaker → loa, mouse → chuột, class → lớp, bus → xe buýt, icecream → kem, steak → bít tết, cake → kêu). Move them to a `vi_native` column or drop them.

Tags used: `cluster`, `cluster3`, `coda_l`, `coda_s`, `coda_z`, `coda_ks`, `coda_t`, `coda_d`, `coda_k`, `coda_stop`, `coda_r`, `coda_v`, `coda_dj`, `coda_nt`, `coda_nk`, `tion`, `ing`, `stress1/2/3`, `open`, `diphthong`, and a few others.

## Patterns from the native-speaker corrections

These are rule candidates. Confirm them against the data through alignment, not by hard-coding.

- w onset → g: sóp goe, goép sai, goai phai, goai (white).
- /oʊ/ → âu, /eɪ/ → ây: sâu, pho lâu, phâu đờ, ô cây, bây bi, đa ta bây.
- z, ʒ, ð → d: đì dai, pô di sừn, pờ ri den tây sừn, vơ dừn, ao go ri dừm.
- Unstressed syllable before the stressed one → huyền: rì pọt, đì dai.
- Unstressed final -er → huyền (ờ): phâu đờ, ma na giờ, pờ lây ờ, sinh gờ. Exceptions keep ngang: sơ vơ, com piu tơ, súp pơ, sờ pích cơ.
- Final l after a vowel → u/o glide: sêu, hô theo. Exception: mall → mô.
- s/sh onset → x in some short words (xóp, xót) but not others (sóp pinh, phát sừn). Treat as lexicon, not rule.
- Schwa → ơ or ư: mơ sin, pai thừn.
- Plosive codas take sắc or nặng (Vietnamese phonotactics): con tếch, láp tốp, rì pọt.

## Pipeline to build

### 1. Split

About 130 dev rows, about 50 locked test rows. Stratify so every tag appears in both. Never tune rules or fit models on test rows.

### 2. Alignment and mapping table

Align each word's ARPAbet phones to its Vietnamese syllables with a small edit-distance or EM aligner. Count which English phone (in context) becomes which Vietnamese onset, glide, nucleus or coda. Output a probability table (e.g. W → g, OW → âu, Z → d). Every later step reads from this table.

### 3. Syllabification into Vietnamese slots

Vietnamese syllable: (onset) (w-glide) nucleus (coda), coda ∈ {p, t, c, ch, m, n, ng, nh, i/y glide, u/o glide}.

- Syllabify English phones with maximal onset.
- Repair clusters by vowel insertion ("sờ", "bờ", "cờ") or consonant deletion; emit both.
- Remap illegal codas (s → t, l → glide or drop, v → p, ks → ch, dʒ → t).

### 4. Tone assignment

Per-syllable features: English stress, position in word, inserted vowel or not, coda type, onset voicing, whether the syllable comes from -er/-tion/-ing.

Start with hand rules (plosive coda → sắc/nặng; inserted vowel → huyền; unstressed final -er → huyền; else ngang). Then fit a shallow decision tree on dev and compare. Keep the tree printable.

### 5. Orthography

Phones plus tone → quốc ngữ: c/k/q, g/gh, ng/ngh, gi/d, tone-mark placement (goép, lóoc). Must round-trip: parse the gold `vi_form` into slots and regenerate the same string.

### 6. Candidates and ranking

- Produce the top N combinations from the mapping table and the cluster/coda variants.
- Filter: panphon feature-weighted distance between English IPA and candidate Vietnamese IPA must stay under a threshold. This is a filter, not the final pick; argmax similarity drifts toward transliteration.
- Rank survivors by naturalness: Vietnamese syllable frequency (count from Vietnamese Wikipedia or another corpus), penalty for rare rhymes and rare onset+rhyme pairs, rule-preference order.

### 7. Evaluation

Report on dev during development and on test at milestones:

- exact match vs `vi_form`
- match vs `vi_form` or any `alt_forms`
- syllable error rate
- tone accuracy, separately
- error breakdown by tag

### 8. Out-of-vocabulary words

CMUdict first; `g2p_en` only when a word is missing.

### 9. Growing the data

Run the generator on the next 1,000 common English words, have a native speaker correct the output, add rows, refit steps 2 and 4.

## Suggested repo layout

```
boi/
  data/eval_v0.csv
  data/splits/{dev,test}.csv
  boi/
    g2p.py          # CMUdict + fallback
    align.py        # step 2
    syllabify.py    # step 3
    tone.py         # step 4
    ortho.py        # step 5
    rank.py         # step 6
    generate.py     # end-to-end
  scripts/build_eval.py
  eval/run_eval.py
  tests/
```

## Milestones

1. Steps 1, 2, 5 (orthography round-trip passes on all 181 gold forms).
2. Steps 3, 4: end-to-end baseline with one output per word; first dev numbers.
3. Step 6 ranking; compare against baseline.
4. Test-set report, then data growth.

## Open questions

- Default inserted vowel: "sờ" vs "xì" (stress → sờ trét or xì trét).
- Whether -er tone exceptions (server, computer, super, speaker) follow a rule or are lexical.
- Southern dialect support later, or Northern only.
