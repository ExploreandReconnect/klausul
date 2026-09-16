# Klausul — PRD

**Version** Hackathon MVP 0.1 · **Market** EU/EEA · **Product** private motor insurance

> Build an EU motor-insurance comparison assistant that converts insurance documents
> into a common structured model, identifies material changes or differences, shows the
> evidence for every finding, explains what those differences mean for the individual
> user, and identifies what the user should clarify before renewing or switching.

Six words: **"Know what changed before you renew."**
Second flow: **"Know what changes if you switch."**

---

## 1. The core transformation

Not a PDF summariser. The chain is:

```
unstructured documents → standardised insurance model → deterministic comparison
                       → personalised explanation → actionable next steps
```

The interesting engineering is not the diff. It is normalisation → evidence →
consequence → personal relevance.

## 2. User

An EU consumer who owns a car, already has motor insurance, has received a renewal or a
competing quote, does not want to read several insurance documents, and wants to know
whether changing insurer actually improves their position. No insurance expertise assumed.

## 3. Entry

Two choices, nothing else in the MVP.

| | |
|---|---|
| **A. My insurance has been renewed** | See what changed |
| **B. I have another offer** | Compare it with my current insurance |

## 4. Flow A — What changed?

Upload the previous policy and the renewal. The system identifies language and document
type, extracts insurer and product, maps both into the canonical schema, compares each
field, classifies each difference, judges likely consumer significance, states its
uncertainty, and generates questions.

The first screen is **not** a document summary. It is a verdict sentence and a count:
how many meaningful changes, how many better, how many worse, how many need checking.
Then the ledger of material changes.

**"Not found" must never automatically mean "not covered."**

## 5. Flow B — Compare offers

Current policy vs alternative offer, both mapped into the same schema. Output groups
into: better in B · worse in B · essentially the same · cannot determine. Then a bottom
line that states the trade-off and names the user circumstance that changes its weight.

Never *"buy Offer B."* The MVP is decision support, not regulated personalised advice.

## 6. Personalisation

Asked **after** upload, never before. At most five to seven questions:

driving frequency · geography (domestic vs regularly elsewhere in Europe) · vehicle
dependency · parking (private vs street) · financial preference (lower premium vs lower
exposure vs balanced) · vehicle value · optionally other or young drivers

**These answers change relevance weighting and explanation. They never change an
extracted fact.** That separation is the architecture, not a detail of it.

## 7. The EU standardisation layer

Directive (EU) 2016/97 requires an IPID for non-life products. Commission Implementing
Regulation (EU) 2017/1469 fixes its presentation and its nine sections, identically
across member states and languages, normally two A4 pages and never more than three.

The IPID is the normalisation backbone, not necessarily the only uploaded document —
the template itself states that complete pre-contractual and contractual information is
provided elsewhere. The app treats other documents as additional sources.

## 8. Canonical model

One JSON representation per document, before any comparison: document metadata, price,
coverage (13 named perils/benefits), coverage limits, excesses, exclusions, geography,
obligations, claims conditions, payment, duration, cancellation, no-claims, and an
explicit `uncertainties` list.

This is an application schema. It is not a claim that EU law mandates each motor-specific
field.

## 9. Provenance on every field

Architectural requirement, not a UI nicety. Every field carries `value`, `unit`,
`status`, `confidence`, `source_document`, `source_page`, `source_text` (verbatim,
untranslated).

Statuses: `explicit` · `inferred` · `not_found` · `not_applicable` · `ambiguous` ·
`conflicting`

The UI lets the user click any result and see where it came from. This makes
hallucination visible rather than plausible.

## 10. Comparison engine

Never ask the model *"which insurance is better?"*

1. **Extraction** — model converts each document to canonical structured data
2. **Validation** — types, currency, dates, inconsistencies, missing fields, contradictions
3. **Deterministic comparison** — application code, producing one of: `same`,
   `better_a`, `better_b`, `different_not_rankable`, `missing_a`, `missing_b`,
   `missing_both`, `uncertain`
4. **Interpretation** — only now does the model explain what a difference means
5. **Personalisation** — profile determines relevance: HIGH / MEDIUM / LOW

The model is not permitted to invent the underlying comparison.

## 11. Better / worse logic

Mechanically rankable, coverage held equal: lower premium better · lower excess better ·
higher monetary limit generally better · broader territory generally better.

Much is not rankable. "Insurer A excludes X; insurer B covers X subject to condition Y"
is `different_not_rankable`. The model may explain the practical difference. It may not
fabricate a score.

## 12. Three layers per difference

Visually distinguished, so interpretation never masquerades as document fact.

| Layer | Example |
|---|---|
| **Fact** | Offer B's theft excess is €500 against €250 in your current policy |
| **Meaning** | You would pay €250 more yourself on an eligible theft claim |
| **For you** | You park on the street, so this deserves more weight than average |

## 13. Action layer

At most five items, each traceable to an unresolved or material finding. Questions to
ask the insurer — considerably more useful than *"Policy A wins 7–5."*

## 14. Guardrails

Never: invent missing coverage · read `not_found` as `not covered` · silently resolve
contradictions · present inference as explicit fact · claim legal certainty · claim to
be a broker · recommend a provider from an opaque score.

Low confidence produces *"we couldn't determine this reliably from the uploaded
documents."* That is a successful answer.

## 15. Language

Accept EU-language documents the model handles reliably. Normalise into
language-independent canonical keys. Output English for the demo; source quotations
preserved in the original language. The IPID framework helps because the semantic
sections stay standardised across languages.

## 16. Scope

**Build:** PDF upload → extraction → normalisation → comparison → personal relevance →
evidence → action.

**Do not build:** insurer search · live quotes · marketplace · purchasing · broker
integration · claims handling · accounts unless required · other insurance types ·
US support · comprehensive legal interpretation.

## 17. Demo

1. *"My renewal arrived. I don't know what changed."* → premium +12.5%, two coverage
   changes, one higher excess, one potentially important benefit that cannot be confirmed
2. Competing quote → saves €126/year, but collision excess +€300, European roadside
   unclear, glass excess €100 lower
3. Profile: 25,000 km/year, drives abroad regularly, heavily dependent on the vehicle →
   relevance reorders; the facts do not move
4. One click: *"Questions to ask insurer"*

## 18. Success criteria

| | |
|---|---|
| Extraction | ≥90% correct on the predetermined comparison fields, on the test set |
| Traceability | every material factual claim links to document evidence |
| Comparison | no invented difference between policies |
| Time | useful comparison in under ~30 seconds |
| UX | a first-time user understands the principal difference within 60 seconds |
| Demo | a judge understands problem and value within the first 15 seconds |

## 19. Architecture

```
Frontend → PDF upload → parser → classification → structured extraction
→ canonical JSON → schema validation → deterministic comparison engine
→ profile weighting → LLM explanation → evidence-linked UI
```

The structured extraction and interpretation layers use the required NVIDIA open model
on Nebius, because multilingual long-document extraction is what that layer genuinely
needs — not because a sponsor's model had to appear somewhere.
