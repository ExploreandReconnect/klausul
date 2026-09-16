# DESIGN.md — the rules an agent must follow in this repo

**Read this before writing any UI in this project.** It is the design constitution:
the agent's job is to *extend* this system, not to invent a parallel one.

This file is also the context file that `impeccable` (`/impeccable init`) reads, so
if that skill is installed it will inherit these rules instead of imposing its own
defaults. See `REFERENCE.md` for how to re-derive the tokens from a product you admire.

---

## Non-negotiables

1. **Never hard-code a colour.** Not a hex, not `rgb()`, not a Tailwind palette
   class (`bg-slate-800`, `text-gray-500`). Every colour comes from a token in
   `app/globals.css`. If a colour you need does not exist, add a *token*, then use it.
2. **Never hard-code a font family or a raw font stack.** Use `font-sans`,
   `font-mono`, or the `.numeric` utility.
3. **Every number wears `.numeric`** — metrics, IDs, timestamps, counts, currency,
   percentages, table cells. Tabular figures are applied globally; this class also
   switches the face and tightens tracking.
4. **`<Metric>` requires a `provenance` prop.** `live | sourced | illustrative | mock`.
   Pick the honest one. A `live` chip on mock data is the one thing that must never
   ship.
5. **One `--focus` element per screen.** `--primary` paints what you click;
   `--focus` paints the single thing the reader came for. Two focus elements on one
   screen is a bug.
6. **Three weights, never one.** `<Card weight="context | default | focus | note">`.
   A screen where every block is a `default` card has depth but does not *read* as
   depth.
7. **Beat labels, not bold sentences.** `<BeatLabel>` / `<Beat>` — an uppercase
   micro-label above a hairline. Never `**Why it matters**` as bold body text.
8. **A caveat travels with its claim.** `<Metric caveat="…">`, `<ChartFrame caveat="…">`.
   Footnote *styling* is fine; footnote *relocation* is not.
9. **Density budget.** Executive view: **4 metrics · 1 chart · 1 summary**. A new
   widget does not get added — it displaces one. Ask before exceeding it.
10. **Motion is 150–250 ms, ease-out, on hover / press / layout only.** Nothing
    decorative. Nothing slower.

---

## Component map — reach for these before writing new ones

| Need | Use | Not |
|---|---|---|
| A number | `<Metric>` | a styled `<div>` |
| A row of numbers | `<MetricRow>` | a bespoke grid |
| A section heading inside a card | `<BeatLabel>` | `<h4 className="font-bold">` |
| A labelled block | `<Beat label="…">` | a bold paragraph |
| A status | `<StatusBadge>` | a coloured dot |
| Where data came from | `<ProvenanceChip>` / `<ProvenanceBanner>` | a footnote |
| A list of things to do | `<ChevronActions>` | a `<ul>` of bullets |
| A card that reacts to the cursor | `<SpotlightCard>` | a hover shadow |
| Tabs / segmented control | `<FluidTabs>` | Radix tabs |
| A table | `<DataTable>` | a raw `<table>` |
| Row / card detail | `<DetailSheet>` | a modal or a new route |
| Nothing to show | `<EmptyState>` | "No data" |
| Waiting | `SkeletonMetric` / `SkeletonRows` / `SkeletonChart` | a spinner |
| A chart | `<AreaTrend>` / `<BarSeries>` / `<Sparkline>` | raw Recharts |
| Streaming model output | `<StreamText>` | rendering the whole string at once |
| A page title | `<PageHeader>` | an `<h1>` |

Everything above is on `/kit`. Open it before asking what exists.

---

## Charts

- Series colours come from `--chart-1..8`, **in that fixed order**. It is a
  validated palette (adjacent-pair colour-vision separation ΔE ≥ 8 in both modes).
  Do not re-order it, do not hand-pick hues, do not generate a ninth.
- **Colour follows the entity, not its rank.** If a filter can change the series
  count, pin `colorIndex` so the survivors do not repaint.
- **One y-axis. Always.** Two measures of different scale → two charts, or index
  both to a common base. A dual-axis chart is the single most common charting error.
- The one override: **if the series IS a status**, pass
  `color: "var(--success | --warning | --danger)"`. Green must never mean "blocked".
- ≥ 2 filled areas overlapping is banned — with two or more series `<AreaTrend>`
  renders as lines. Fill is for a single series only.
- A legend appears for ≥ 2 series and never for one (the title names it).

---

## Anti-patterns — these are the AI tells

Reject these in review, whoever wrote them:

- Inter, Arial, Helvetica, or a bare system stack as the display face
- Purple-to-blue gradient headings; glassmorphism; `backdrop-blur` on everything
- Emoji used as iconography
- A card inside a card inside a card
- Grey body text on a coloured background
- `transition: all`, `ease-in-out` on interaction, anything over 300 ms
- Drop shadows you can see as shadows
- Placeholder copy: `Lorem ipsum`, `foo`, `bar`, `Item 1`, `John Doe`, `example@example.com`
- A number without a provenance chip
- Centre-aligned body text in a data UI
- Six accent-coloured elements on one screen
- A spinner where a shaped skeleton belongs

---

## When you add a screen

1. Name the **one decision** the screen serves. Put it in `<PageHeader title>` as a
   sentence, not a label. "Records" is a label; "Four records need review before
   Friday" is a title.
2. Decide what is **context**, what is **the answer**, what is **working notes**.
   Draw them at three different weights.
3. Name the **beats** of the answer. If you cannot name them, the content has no
   structure yet and no styling will supply one.
4. Give it an **empty state, a loading state, and an error state** before you call
   it done.
5. Run `npm run shots` and **look at the screenshots** in both themes.
6. Run the blur test: squint until the words are unreadable. Can you still follow
   the argument from the shapes? If not, it is a bullet wall with headings.

---

## Verification

```bash
npm run build     # must pass
npm run lint      # must be clean — zero errors
npm run shots     # renders every page × 2 themes × 3 presets to ./design-review/
```

Never mark UI work complete without looking at the output of the third one.
