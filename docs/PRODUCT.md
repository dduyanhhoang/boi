# Boi

## What it is

A rule-based generator that turns an English word into how Vietnamese speakers
actually read it, written as Vietnamese syllables with tones ("tiếng Anh bồi").
Northern dialect, colloquial. The Python package is the product; the web app at
`app/` is a playground for it.

## Unique mechanism

Nativization, not transliteration. Every output is a legal Vietnamese syllable,
and the path from English phones to Vietnamese letters is a readable table plus
four tone rules, so any output traces back to a named rule. No neural model.

## Audience and scene

Vietnamese speakers and people learning how Vietnamese absorbs English, plus
linguists looking at loanword adaptation. The scene for the playground: someone
sent a link, opens it on a phone or laptop, types one or two words they are
curious about, and wants to see the answer and why it came out that way. A
minute of use, not a daily tool.

## What the playground must prove

That the generator is real and traceable. Typing a word returns a reading, the
syllables it is built from with their tones, and the English phones it started
from. For the 181 reviewed words it also shows what the native speaker wrote,
including where the generator disagrees. Hiding the disagreements would make
the demo a lie.

## Constraints

- GitHub Pages is static. The generator is Python, so readings for all 117,485
  CMUdict words are precomputed into letter shards the browser looks up.
- A word outside CMUdict has no reading, since that path needs `g2p_en`.
- Visual authority is the owner's Notion UIUX spec, SPEC-001 Core and SPEC-002
  Web: Apple HIG, Liquid Glass, semantic tokens, WCAG 2.2 AA.

## Non-goals

No accounts, no persistence beyond the theme choice, no editing of the data
from the web, no Southern dialect.
