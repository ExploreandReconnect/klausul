# The corpus — method, rules, and what it has already taught us

The success criterion in the PRD is *"≥90% correct extraction of the predetermined
comparison fields."* Against documents we wrote ourselves that number means nothing:
it measures how well the extractor reads our own assumptions. This is the apparatus
that turns it into a fact.

---

## The rule this obeys

> We do not scrape. A source with no documented machine route is registered as
> blocked with a probe date and a drafted contact email, never scraped.

`tools/fetch_corpus.py` implements that literally:

- only entries marked `route: open` are ever fetched;
- one request per document — no crawling, no link-following, no discovery;
- `robots.txt` is read for the host, and a disallow turns the entry into
  `route: blocked` with today's date instead of a download;
- a 403, a 404, an off-host redirect or a non-PDF response is recorded as blocked
  and **never retried by another method**;
- every blocked entry gets a drafted email written to `corpus/contact/`.

`corpus/register.yaml` is therefore the single record of what is reachable and what
needs a human to write to somebody. A blocked source is a task, not a silence.

```bash
python tools/fetch_corpus.py --probe            # check routes, change nothing
python tools/fetch_corpus.py --market IE        # download the open ones
```

Run it on your own machine. It is written to be run by you, against your own
documented routes, and the documents land on your disk under your control.

---

## Why these three markets

The IPID's *container* is harmonised by Commission Implementing Regulation (EU)
2017/1469. Its contents are not. So markets were chosen so that no two test the
same failure mode:

| Market | Tests | Documents |
|---|---|---|
| 🇩🇰 **Denmark** | **Non-euro (DKK)**, Danish, comma decimals | 10 |
| 🇩🇪 **Germany** | German, SF-Klassen bonus system, comma decimals | 10 |
| 🇮🇪 **Ireland** | **English**, euro, **point decimals** | 10 |

Ireland earns its place twice over: it is the only large market with point decimals,
and English means ground truth can be hand-labelled in minutes rather than guessed.
**Labelling, not fetching, is the real constraint** — thirty documents × eighteen
fields is about five hours of careful reading, and it has to be a language you read.

France (Romance vocabulary, statutory *coefficient de réduction-majoration*) and the
Netherlands are carried in the register unprobed, as the phase-two extension. Because
the sections are fixed, a new market is mostly a `app/vocab.py` entry rather than new
engineering — which is the point worth making in the submission.

---

## What the first two sources already changed

Two documents in, and both overturned a design assumption. This is the argument for
doing the corpus before anything else is built on top of the extractor.

### 1. Section order is not reliable — matching must be semantic

EIOPA states plainly that manufacturers *"are not obliged to use these specific files
and may choose instead to develop their own IPIDs that meet the requirements of the
IPID Implementing Regulation."*

The Aviva Ireland motor IPID proves what that means in practice. It carries **eight
sections, not nine** — *"What is this type of insurance?"* is absent — and the order
deviates from the Annex: restrictions appear **after** territory, and cancellation
**before** start-and-end.

**Fixed:** `app/extract.py` now instructs the model to locate sections by meaning and
to report a genuinely absent section in `uncertainties` rather than borrowing content
from a neighbour. `app/vocab.match_section` matches on any language's surface form.

### 2. Conditional amounts and time-limited territories do not fit a scalar

The same document carries a standard excess of €300 **plus** a conditional €2,500
where penalty points were not declared; a courtesy car only if the insurer's own
repair network is used; and a territory that is a **list plus a time limit** —
*"identical cover in the EU for up to 31 days."*

Flattening any of those into one number is exactly the dishonesty the provenance
envelope exists to prevent. €300 and €2,500 are not one excess.

**Fixed:** `ConditionalAmount` in `app/schema.py`, two new comparison dimensions
(`foreign_days`, `excess_conditional`), and explicit worked examples for conditional
values in the extraction prompt.

---

## The number formats, which are a 100× bug if guessed

| Market | Decimal | Thousands | Currency | Example |
|---|---|---|---|---|
| DK | `,` | `.` | DKK | `1.234,56 kr.` |
| DE | `,` | `.` | EUR | `1.234,56 EUR` |
| IE | `.` | `,` | EUR | `€1,234.56` |
| FR | `,` | space | EUR | `1 234,56 €` |
| NL | `,` | `.` | EUR | `€ 1.234,56` |

```
parse_amount("2,500", "IE") == 2500.0
parse_amount("2,500", "DE") ==    2.5
```

The same three characters, a thousandfold apart. This is why `extract()` takes a
`market` argument and refuses to guess — an unknown market returns `None` rather
than a plausible number.

---

## Labelling and scoring

```bash
python tools/score_extraction.py --make-labels     # blank sheet, one row per doc × field
# fill corpus/labels/labels.csv by hand
python tools/score_extraction.py                   # run the extractor and score it
```

`true_status` is `explicit`, `ambiguous` or `not_in_document`. Leave `true_value`
blank for `not_in_document`.

The scorer is deliberately harsher than a single accuracy figure:

| Verdict | Meaning |
|---|---|
| `correct` | right value **and** a source quote |
| `correct_unsourced` | right value, no quote — **counted as a failure**, because the promise is traceability, not luck |
| `correct_absence` | the document really is silent, and we said so. A success |
| `missed` | the document stated it; we said not found |
| `false_positive` | the document is silent; we produced a value. **The dangerous one** |
| `wrong` | a confident wrong figure. The failure that actually hurts a consumer |

A single percentage hides which of those you have, so the report always prints the
breakdown, the per-market split, and the eight weakest fields.

---

## Vocabulary verification

`app/vocab.verification_state()` reports what the table still owes:

```
sections_verified: 8/45        (only English, from the Aviva Ireland IPID)
field_language_pairs: 100      verified: 0
```

Every Danish, German, French and Dutch term in `app/vocab.py` is a translation we
believe in, not one we have seen in a published document. Raising a term to
`verified` requires a real document. **A term still unverified after the corpus run
is a gap to report in the README, not a detail to leave quiet.**

---

## Status

| | |
|---|---|
| Sources registered | **31** (10 DK · 10 DE · 10 IE · 1 EU reference) |
| Routes confirmed open | **2** |
| Routes to probe | **29** |
| Documents downloaded | **0** |
| Fields labelled | **0** |
| Measured accuracy | **not yet measured** |

Next: run `--probe`, send the contact emails the blocked entries generate, label,
score. The accuracy number goes in the README and the video only once this table
has real figures in it.
