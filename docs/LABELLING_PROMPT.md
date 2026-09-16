# The labelling prompt

Paste everything between the rules below into **ChatGPT, Gemini and Grok separately**,
attaching **one document at a time**. Do not show any model another model's answer —
independence is the only thing that makes their disagreement informative.

Save each reply as `corpus/labels/raw/<doc_id>.<model>.csv`
(e.g. `corpus/labels/raw/ie-aviva-motorcare.gpt.csv`).

Then run `python tools/merge_labels.py`. It verifies every quote against the real PDF
text, agrees what can be agreed automatically, and hands you only the rows that need
a human.

---

## ✂️ — paste from here —

You are helping build a **ground-truth evaluation set** for an open-source research
project. Your output is used to *measure* an automated extractor, so your job is
accuracy and restraint, not helpfulness. **A wrong confident answer is far worse than
"not in document."**

### Context

EU insurance law (Directive (EU) 2016/97, and Commission Implementing Regulation (EU)
2017/1469) requires every non-life insurance product sold in the EU to carry an
**Insurance Product Information Document (IPID)** — a short standardised summary with
nine prescribed sections. The regulation harmonises the *structure*. It does not
harmonise language, terminology, currency, number format, or national product design.

I am attaching one real IPID (or policy document) for a private motor insurance
product. I need you to record what it actually says about 18 specific fields.

### The seven rules

1. **Never infer. Never complete. Never normalise.** Record only what is written.
2. **Silence is an answer.** If the document does not state something, the status is
   `not_in_document`. This is a *correct* label, not a failure. Do **not** reason that
   a benefit is "probably standard" or "usually included."
3. **Absence is not exclusion.** A field the document never mentions is
   `not_in_document`. A field the document explicitly excludes is `explicit` with the
   value `false`. These are different and must never be merged.
4. **Quote verbatim, in the document's own language.** Do not translate, tidy,
   shorten or paraphrase. The quote will be checked character-by-character against the
   PDF text; a quote that does not appear exactly will be rejected automatically.
5. **Give the page number the quote appears on.**
6. **Conditional values are `ambiguous`, never flattened.** If an excess is €300 but
   rises to €2,500 in some circumstance, the general excess is `300` and the €2,500
   belongs in `excesses.conditional_max` with its condition. If a benefit applies only
   under a condition ("no excess on repair; on replacement clause 7.3 applies"), the
   status is `ambiguous` and the note states the condition.
7. **Use the market's number convention.** It is given below. Report a plain number
   with no separators. Do not convert currencies.

| Market | Decimal | Thousands | Currency | Example |
|---|---|---|---|---|
| DK | `,` | `.` | DKK | `1.234,56 kr.` |
| DE | `,` | `.` | EUR | `1.234,56 EUR` |
| IE | `.` | `,` | EUR | `€1,234.56` |
| FR | `,` | space | EUR | `1 234,56 €` |
| NL | `,` | `.` | EUR | `€ 1.234,56` |

`2,500` is **two thousand five hundred** in IE and **two point five** in DE. Getting
this wrong is a thousandfold error, so read the market line before any amount.

### Find sections by meaning, not by position

Real IPIDs deviate from the prescribed order. EIOPA confirms manufacturers may build
their own document, and published IPIDs exist with **eight** sections rather than
nine, with headings merged, and in a different order. Locate what you need by what it
says. If a section genuinely is not there, that is `not_in_document`, not a reason to
borrow from a neighbouring section.

### The 18 fields

| field | what it means |
|---|---|
| `price.annual_premium` | The annual premium. Usually absent from an IPID — that is fine, say so |
| `excesses.general` | The standard/basic excess, deductible, franchise, selvrisiko, Selbstbeteiligung, eigen risico |
| `excesses.collision` | Excess on damage to the insured's own vehicle in an accident (comprehensive / kasko / Vollkasko) |
| `excesses.theft` | Excess on an accepted theft claim |
| `excesses.glass` | Excess on windscreen or glass damage |
| `excesses.young_driver` | Additional excess for a young or inexperienced driver |
| `excesses.conditional_max` | The **highest conditional** extra excess, with its condition in `note` |
| `coverage_limits.third_party_liability_property` | Maximum sum insured for third-party **property** damage |
| `coverage_limits.legal_assistance` | Maximum sum insured for legal expenses / retshjælp / Rechtsschutz |
| `coverage_limits.replacement_vehicle_days` | Maximum days of courtesy / replacement vehicle |
| `coverage_limits.foreign_use_days` | Days of cover outside the home country, if time-limited |
| `coverage.roadside_assistance` | `true` / `false` — breakdown assistance, vejhjælp, Schutzbrief, pechhulp |
| `coverage.foreign_travel` | `true` / `false` — cover while driving abroad |
| `coverage.theft` | `true` / `false` — theft cover |
| `coverage.windscreen_glass` | `true` / `false` — glass cover |
| `coverage.legal_assistance` | `true` / `false` — legal expenses cover |
| `territories` | The countries or regions covered, as written |
| `no_claims` | No-claims discount / bonus-malus / Schadenfreiheitsrabatt / skadefri kørsel terms |

### Output

Return **only** a CSV with exactly this header and one row per field, all 18 rows,
in the order above. No commentary before or after.

```
doc_id,field,true_value,unit,true_status,page,quote,note,your_confidence
```

- `true_status` — one of `explicit`, `ambiguous`, `not_in_document`
- `true_value` — a plain number, `true`, `false`, or a short text value.
  **Leave blank when the status is `not_in_document`.**
- `unit` — `EUR`, `DKK`, `days`, or blank
- `page` — the page number the quote is on; blank if `not_in_document`
- `quote` — verbatim, original language. Blank if `not_in_document`.
  Wrap in double quotes and double any internal double-quote.
- `note` — the condition, if the status is `ambiguous`. Otherwise blank.
- `your_confidence` — 0.0 to 1.0, your own honest probability that this row is right

### What I am attaching

```
doc_id:  <PASTE THE ID FROM corpus/register.yaml>
market:  <DK | DE | IE>
language:<da | de | en>
insurer: <NAME>
```

If you cannot read the attached document, say so plainly and return nothing else.
Do not reconstruct it from knowledge of the insurer.

## ✂️ — paste to here —

---

## Why three models and not one

They are not voting on the truth. They are being used as three independent readers so
that **their disagreement points a human at the rows that are actually hard**.

`tools/merge_labels.py` then applies, in order:

1. **Quote verification — mechanical, no judgement.** Every quote is checked against
   the PDF's own extracted text. A quote that does not appear verbatim is rejected and
   that model's row is discarded. This removes hallucinated evidence deterministically,
   and it is the same principle the product itself runs on.
2. **Unanimous + verified → accepted**, with a 10% random sample flagged for you
   anyway, so the accept rule is itself measured.
3. **Any disagreement → adjudication queue** for you, with the three answers and the
   three quotes side by side.
4. **Unanimous `not_in_document` → accepted but flagged.** Three models agreeing that
   something is absent is the *weakest* kind of agreement, because they share the
   habit of overlooking a clause in a language none of them reads natively.

## The arithmetic

| | |
|---|---|
| Cells to label | 30 docs × 18 fields = **540** |
| Expected unanimous + quote-verified | ~65–75% |
| Rows reaching you | **~135–190**, plus a 10% audit sample |
| Your time | **~1.5–2 hours**, down from 5 |

That is a real saving, and unlike the shortcut it does not hollow out the number.

## What you must say in the README

> Ground truth was produced by three independent frontier models, filtered by
> mechanical verbatim-quote verification against the source PDF, with all
> disagreements and a 10% sample of agreements adjudicated by a human.
> Inter-annotator agreement before adjudication: **XX%**.

That sentence is defensible. *"Labelled by GPT, Gemini and Grok"* on its own is not,
and a judge who has built an evaluation set will know the difference immediately.
