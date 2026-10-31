# Design

Visual authority is the owner's Notion spec, not this file. This file records
the token values resolved from it, which that spec leaves as TBD, and the one
place this project extends it.

- SPEC-001 Core: Apple HIG, Liquid Glass, semantic tokens, concentric radii,
  capsule controls, WCAG 2.2 AA floor.
- SPEC-002 Web: archetype **web app**. Glass on the functional layer only
  (toolbar and floating controls). Content is opaque. No glass on glass.

Mode: Operate. The visitor types a word and reads an answer. Scanability and
state handling outrank expression; the character lives in the detail.

## Tokens

Values are Apple's published system colours and iOS text styles, resolved by
the owner on 2026-10-30. Implemented in `app/styles/tokens.css`.

Colour, four variants per token (light, dark, light increased contrast, dark
increased contrast): `bg`, `bg-grouped`, `bg-elevated`, `label`,
`label-secondary`, `label-tertiary`, `separator`, `accent`, `accent-wash`,
`destructive`, `success`, `warning`. Accent is systemBlue `#007AFF` / `#0A84FF`,
and `#0040DD` / `#409CFF` at increased contrast.

Type: Apple's iOS text styles by name, Large Title 34/41 down to Caption 2
11/13, in rem against a 16px root. **One addition to the spec scale:** a
`Display` step above Large Title, `clamp(2.5rem, 7.5vw, 4.25rem)` with -0.03em
tracking, used only for the generated reading. The reading is the one thing on
the page the visitor came for, and Large Title does not carry it.

Spacing: base 4, rhythm 8, scale `4 8 12 16 24 32 48 64`.

Radius: capsule for controls, 12 cards, 20 containers, 28 the input. Children
are concentric: child radius = parent radius − the padding between them.

Motion: 180ms state, 280ms enter and exit, 420ms the one authored moment;
`cubic-bezier(.32,.72,0,1)`. Under `prefers-reduced-motion` everything becomes
a 120ms opacity fade.

## Type stack

`-apple-system, BlinkMacSystemFont` first, so Apple devices render in the real
system font with nothing downloaded, then self-hosted Inter Variable subset to
latin plus Vietnamese (`app/fonts/inter-vi.woff2`, 118KB, weights 100 to 900),
then `system-ui, sans-serif`. Monospace is `ui-monospace, SFMono-Regular,
Menlo, monospace` with `tabular-nums`, used for ARPAbet only, which is data.

SF Pro is deliberately not self-hosted. The owner's spec allows Apple fonts in
personal projects, but this ships to public GitHub Pages, and serving Apple
font binaries publicly is the case their licence excludes. Decided with the
owner on 2026-10-30.

## The authored moment

The result composes once per lookup: the reading rises 8px and fades in while
the syllable chips stagger in from `blur(6px)`. Disabled under reduced motion.

A second moment follows it, and only one other: the derivation plays itself
through from 480ms, a stage every 320ms, after the reading has landed. The
owner asked for the answer first and the working second, and a sequence is
the one thing a static list cannot show. It replaces the `How it got there`
disclosure, which hid the derivation behind a click nobody made. `Play again`
replays it; under reduced motion all three stages are simply present.

Nothing else on the page animates beyond its own state change.

## The derivation

Three stages on one 1px thread, a dot per stage, the last dot in `accent`:
the word, its sounds as ARPAbet chips, and which sounds became which
syllable. Not three cards — a stack of same-shaped boxes would make the
sequence look like three unrelated facts, and the thread is what says one
thing became the next.

The grouping is the one the generator actually chose, not an alignment drawn
by eye: `candidatesFromPhones` takes a `collect` map and hands back the slots
behind the winning reading. It needs the browser pipeline, which loads after
the first paint, so the stage fills in behind the answer rather than holding
it up. A memorised reading has no slots behind it and says so.

There is no replay control. The sequence plays once on arrival; a button to
watch it again is a control for a thing nobody asked to repeat.

## Emphasis

Per SPEC-001, emphasis is a wash background plus same-tone text, never an
underline, a rule, or a symbol beside the word. Two kinds on this surface and
no more: `accent-wash` for the syllable under the pointer or keyboard focus,
and `warning` wash for a reviewed word whose gold reading differs from the
generated one. Both carry their meaning as text in the pill, so colour is never
the only channel.

## The second reading (removed 2026-10-31)

The letter reading and the Ngo comparison used to sit on a line under the
syllables. The owner removed them: on a page whose job is one answer, three
competing readings is the demo arguing with itself. `docs/PRODUCT.md` still
wants the disagreements visible, and the reviewed-reading note under the
syllables is where that now lives.

## How it used to work

A word carries two readings: the heard one, from CMUdict, and the letter one.
The page leads with the heard reading and puts the letter reading on a quiet
line directly under the syllables, as a capsule that swaps in when clicked. It
first sat inside "How it got there", where nobody found it. It is not a third
emphasis style: it carries no wash, only a secondary label and a bordered
capsule, so the two-emphasis rule still holds.

## The wide layout

Below 70rem the result is one column, which is the phone composition and the
one most visits use. At 70rem and above the derivation moves beside the
answer and `main` widens to 54rem, so the screen is read as answer-then-
working across rather than down, and the page stops being a narrow column
with the right half of the screen empty.

The second column hugs the derivation rather than stretching to the grid, so
the width that is left is the page's margin and not an empty cell. `footer`
takes the same width as `main` at that breakpoint; its own rule sits later in
the file than the layout block, so the override has to sit later still.

Everything on the page shares one left edge, with the derivation as the only
second. The derivation's phone column is `max-content`, which lets the rows
start at their own heading's edge while the arrows stay aligned to each other.

Running text in the footer is Subheadline, not Footnote. Footnote is 13px and
these are paragraphs; the scale was right and the role was not.

## Getting back

The wordmark is a real link to `./`, so it reads as a link, opens in a new
tab, and offers its context menu. In this tab it resets in place rather than
reloading the shards. Before it, a lookup had no route back to the empty
state but the browser's own Back button.

## Icons

Authored inline SVG on Lucide's geometry: 24px box, 1.75px stroke, round caps
and joins. Six of them (search, clear, submit, theme, source, external). No
emoji, no glyph substitutes. Each has a label for assistive tech.
