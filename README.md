# boi

boi turns an English word into the way Vietnamese speakers say it, written as Vietnamese syllables with tones. The name comes from *tiếng Anh bồi*, the nativised English of everyday Vietnamese speech.

[Try it in the browser](https://dduyanhhoang.github.io/boi/).

```
$ uv run boi information schedule temperature english software
information     in phô mây sừn
schedule        sờ ke đùa
temperature     tem pơ rây chờ
english         inh lích
software        sóp goe
```

Every syllable it writes is one a Vietnamese speaker can say. The dialect is Northern and colloquial.

## How it works

![The pipeline, with schedule worked through it](docs/pipeline.png?v=2)

The rules are written by hand, so every syllable traces back to the rule that produced it. A short lexicon covers the readings no rule predicts.

## Use

Needs [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run boi laptop wifi website
uv run boi --all database      # ranked alternatives
uv run boi --read ecology      # read off the letters: ê cô lô gi
```

Any word works. 117,496 have a pronunciation in CMUdict, and the rest are read off their spelling.

## How well it works

The eval has 181 readings, each checked by a native speaker, split 131 for development and 50 for testing. The rules were written against the development set.

| | dev | test |
|---|---|---|
| exact match | 0.878 | 0.780 |
| rules alone, no lexicon | 0.847 | 0.760 |

Seven test rows were seen during development. Over the other 43, the rules alone score 0.744. [docs/EVAL.md](docs/EVAL.md) has the details.

## Develop

```sh
uv run pytest                          # 661 tests
uv run eval/run_eval.py dev --errors   # what dev still gets wrong
uv run scripts/build_web_data.py       # data for the playground, then:
python3 -m http.server --directory app # localhost:8000
```

The playground is in `app/` and deploys to GitHub Pages on every push. The design is in [docs/DESIGN.md](docs/DESIGN.md) and the original brief in [docs/brief.md](docs/brief.md).
