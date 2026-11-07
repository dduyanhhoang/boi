# Design

Behaviour follows the owner's Notion spec; this file records the look and the
token values, which that spec leaves as TBD, and the places this project
extends it.

- SPEC-001 Core: Apple HIG, semantic tokens, WCAG 2.2 AA floor.
- SPEC-002 Web: archetype **web app**.

The look is the owner's flat "achromatic ledger", the one their QE apps moved
to on 2026-11-04 (`asr_qe_model`, `docs/superpowers/specs/2026-11-04-qe-tools-hub-design.md`).
It replaces SPEC-001's Liquid Glass and rounded corners: square corners
everywhere, 1px rules, no glass, no shadow, no blur, no gradient, chrome
without colour, and one hue for data. Adopted here on 2026-11-07, keeping
everything else on this page.

Mode: Operate. The visitor types a word and reads an answer. Scanability and
state handling outrank expression; the character lives in the detail.

## Tokens

Colour values are the ledger's, the same table as the QE apps' `ui.css`; type
is Apple's iOS text styles, resolved by the owner on 2026-10-30. Implemented
in `app/styles/tokens.css`.

Colour, four variants per token (light, dark, light increased contrast, dark
increased contrast), each written once as `light-dark()` so the appearance
toggle and the system setting share one list: `bg` (ground `#f8f8f8` /
`#000`), `bg-elevated` (surface), `bg-sunken` (raised), `rule` (the hover
step), `separator`, `control` (a control's border), `label`,
`label-secondary`, `label-tertiary`, `accent`, `accent-ink`, `data`,
`data-wash`, and `destructive`, `success`, `warning` with a wash each.

`accent` is ink, not a hue: `#141414`, inverted on dark. It draws focus rings,
the primary button and anything selected. The one hue is `data`, `#1D5FBF` /
`#5B94E8`, and it goes only on the reading's parts. Every text token measures
4.5:1 or better on every ground it sits on, in all four variants.

Type: Apple's iOS text styles by name, Large Title 34/41 down to Caption 2
11/13, in rem against a 16px root. Weights are the ledger's 400 and 500; 700
is reserved for a headline number, which this page has none of. Figures are
tabular everywhere. **One addition to the spec scale:** a
`Display` step above Large Title, `clamp(2.5rem, 7.5vw, 4.25rem)` with -0.03em
tracking, used only for the generated reading. The reading is the one thing on
the page the visitor came for, and Large Title does not carry it.

Spacing: base 4, rhythm 8, scale `4 8 12 16 24 32 48 64`.

Radius: none. Panels, controls, chips, pills, menus and the favicon are all
square; `* { border-radius: 0 }` also stops the browser rounding its own.

Depth is a step of ground, never a shadow: hover takes `rule`, press and
selection `bg-sunken`. The toolbar sits on the page's ground and gains a 1px
rule once the page has scrolled under it. The suggestion list is a 1px
`control` border on the surface.

Motion: 120ms state, 200ms for anything that opens, 280ms at most, the
authored moment included; `cubic-bezier(.16,1,.3,1)`. Things that open come
8px from their control. Under `prefers-reduced-motion` everything becomes a
120ms opacity fade.

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
the syllable chips stagger in, each rising 6px. Disabled under reduced motion.
The chips used to sharpen from a blur; the ledger has no blur, so they rise.

A second moment follows it, and only one other: the derivation plays itself
through from 480ms, a stage every 320ms, after the reading has landed. The
owner asked for the answer first and the working second, and a sequence is
the one thing a static list cannot show. It replaces the `How it got there`
disclosure, which hid the derivation behind a click nobody made. `Play again`
replays it; under reduced motion all three stages are simply present.

Beyond these two and the empty page's demonstration below, nothing on the
page animates beyond its own state change.

## The demonstration

The empty page shows the tool working before anyone types: under the search
field, an example word is taken through the pipeline, then the next, round
and round. The word rises in, its sounds fade in one at a time, then 1px rules
divide them into syllables, which rise in the data hue with their tones
under them. Each word holds for 2.6s and fades out.

The ledger allows no decorative animation and no effect on page load. This is
neither: it is the tool's real output, the same grouping the derivation
shows, built from the browser pipeline with the examples' phones, and it uses
only the page's own motion, a fade or an 8px rise at 120 to 200ms. The owner
asked for it.

It pauses while the pointer or keyboard focus is on it, while it is off
screen and while the tab is hidden. Its pause button is there because WCAG
2.2.2 asks for one on anything that moves for longer than five seconds.
Under reduced motion it starts paused on a finished word. Clicking the word
opens it.

## The derivation

Three stages on one 1px thread, a square dot per stage, the last in `data`:
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
no more: `data-wash` with `data` text for the syllable under the pointer and
for a reviewed reading the generator matches, and `warning` wash for one it
does not. Both carry their meaning as text in the pill, so colour is never
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

## The empty page

A visitor arriving cold used to see the wordmark, a search field and ten bare
words, and had to read the footer to learn what any of it was for. The empty
page now opens with one line in Large Title saying what this is, and each
example shows its reading under the word, so the page demonstrates the tool
before anyone types. The readings travel in `index.json`, so this costs no
shard fetch.

The line is a paragraph, not a heading. The app's one `h1` is the wordmark on
every view, because an app screen names itself in its shell and the reading
on a result is the content under that name, not its title. Making the
reading the `h1` read better in the markup and broke that convention; the
live region announces the reading to a screen reader either way.

The example chips hold two lines, the word over its reading, and are 44px at
the least, Apple's minimum target.

A shared link opens on a result, and the empty page used to paint first and
then vanish when the script arrived. A line in the head marks the page before
the body is drawn and the script lifts it once the result is up, in a
`finally` so a failed lookup cannot leave the page blank.

## Getting back

The wordmark is a real link to `./`, so it reads as a link, opens in a new
tab, and offers its context menu. In this tab it resets in place rather than
reloading the shards. Before it, a lookup had no route back to the empty
state but the browser's own Back button.

## Icons

Authored inline SVG on Lucide's geometry, drawn the ledger's way: 24px box,
1.5px stroke, square caps, mitred joins. Six of them (search, clear, submit, theme, source, external). No
emoji, no glyph substitutes. Each has a label for assistive tech.
