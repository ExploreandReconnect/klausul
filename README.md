# Klausul

**EU motor insurance, read with its own evidence.**

*Klausul* is Danish, German, Norwegian and Swedish for **clause** — the unit this product
works in. Every figure it shows is a clause, quoted verbatim, with a page number and a
confidence score.

Upload two insurance documents. Klausul shows what differs, cites the exact sentence
behind every finding, and draws what neither document settles — which, in the documents
we have tested, is usually most of it.

Built for the **Nebius x NVIDIA Global AI Hackathon** · track: Best Apps and Agents ·
runs on **Nebius Token Factory** using **NVIDIA Nemotron 3**.

- Live: <https://exploreandreconnect.github.io/klausul/>
- API health (self-reports both Nemotron model IDs): <https://klausul-api.onrender.com/health>
- API docs: <https://klausul-api.onrender.com/docs>
- Models, sizes, and where Token Factory accelerated the workflow:
  [Nebius Token Factory and NVIDIA Nemotron](#nebius-token-factory-and-nvidia-nemotron)

---

## Start here: the thing we got wrong

This began as a tool for comparing insurance renewals. Then we collected the documents.

**Fourteen published Insurance Product Information Documents, from Denmark, Germany and
Ireland. One of them states an excess amount.** The Danish ones contain no money figures
at all. A real Tryg renewal pair, 2022 against 2024, is 94% identical text and has nothing
to compare: no premium, no excess, no limits.

So the original demo — a Danish renewal where a theft excess moved from €300 to €500 and
a replacement-car cap was halved — described a document format that does not exist. It
was invented, and it was wrong.

We kept the product and changed the claim. **The finding is not usually "this number
moved". It is "the document names the cover and never gives you the number."** An IPID
describes the product; your premium and your excess live on the policy schedule, which is
a different document, and nobody compares it.

Everything below follows from that.

---

## Nebius Token Factory and NVIDIA Nemotron

Two Nemotron variants, chosen for two different jobs. The live service self-reports both at
[`/health`](https://klausul-api.onrender.com/health).

| Stage | Model | Why this size |
|---|---|---|
| Extraction | `nvidia/nemotron-3-super-120b-a12b` | Multilingual structured extraction under a strict schema: Danish, German and Irish-English documents into one canonical model, with a verbatim untranslated quote and a page number on every value. German IPIDs arrive embedded in 40-70 page policy packs (~300,000 characters), so real cross-lingual competence and long context were required. The MoE active-parameter count kept latency acceptable: two 2-page documents extract concurrently in 57-145 s. |
| Explanation | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | Called **only after** a difference has been confirmed by deterministic code, so the job is short, bounded prose about one confirmed finding. A 120B model would waste latency and tokens on that. Nano runs 5-16 of these concurrently, 36-60 s total. |

Splitting by job rather than using one model for everything is the same principle the whole
product runs on: use the smallest thing that can do the step correctly.

### Where Token Factory accelerated the workflow

1. **The OpenAI-compatible endpoint.** One base-URL change and an existing client worked --
   zero integration work. That sounds small and is not: the interesting problems got the week
   instead of the plumbing. It also keeps this project portable, which is the right thing for
   an open-infrastructure platform to offer.
2. **Both model sizes behind one endpoint and one key.** The architecture calls a 120B model
   for extraction and a 30B model for explanation inside the same request cycle. One
   credential and one client made that split a design decision rather than an infrastructure
   project. Two providers and it would have been one model doing both jobs badly.
3. **Throughput under concurrency.** The pipeline extracts two documents concurrently, then
   fans out 5-16 explanation calls at a concurrency of 4, with no rate-limit gymnastics.
   End-to-end latency for a full two-document comparison is roughly 100-180 s.

### The prompt line that mattered most

`detailed thinking off` as the first line of the system prompt. Without it, Super spent its
token budget deliberating and returned truncated JSON that never closed. With it, output was
clean and roughly 3x faster. It was the single highest-leverage line in the project and it was
found by accident -- which is why it is written down here.

Extraction prompts are in the repo. Nothing about the method is hidden: the point of using an
open model is being able to say *here is exactly what was sent and what came back.*

---

## The one thing that makes this different

**The model is never asked which policy is better.**

That question is where document-comparison products fail. A model asked to rank two
policies will produce a confident ranking whether or not the documents support one.

So the pipeline splits the job:

| Stage | Who does it | Why |
|---|---|---|
| 1. Text + page map | `pdfplumber` | Page numbers must survive, or citation is impossible |
| 2. Extract to canonical JSON | **Nemotron 3 Super** | Six languages, long documents, one schema |
| 3. Provenance validation | code | A value with no quote behind it is demoted, not trusted |
| 4. **Absence verification** | **code, no model** | A negative from one model pass is an unverified claim |
| 5. Comparison | **code, no model** | A difference in the output appeared in the documents |
| 6. Relevance weighting | **code, no model** | Circumstances change what matters, never what is true |
| 7. Explanation | **Nemotron 3 Nano** | Only now: what does this confirmed difference mean? |

The model extracts. Code decides. The model then explains what code decided.

`app/compare.py` contains no model call. That is not an optimisation; it is the product.

---

## Provenance is the schema, not a feature

No bare value ever enters the comparison engine. Every field is this:

```json
"excesses.general": {
  "value": 300,
  "unit": "EUR",
  "status": "explicit",
  "confidence": 0.96,
  "source_document": "ie-aviva-motorcare.pdf",
  "source_page": 1,
  "source_text": "Policy Excess options – the standard excess is €300 (this is the amount you will have to pay towards the cost of a claim)."
}
```

That is a real field from a real run over a real published IPID; it is in
`web/demo-ie.json`, which ships with the page.

`source_text` is verbatim and untranslated. Six statuses are possible:

`explicit` · `inferred` · `not_found` · `not_applicable` · `ambiguous` · `conflicting`

**`not_found` never becomes `not covered`.** An absence is reported as an absence, and
turned into a question for the insurer. In consumer insurance that distinction is not a
nicety — silently reading a missing clause as "no cover" is how a comparison tool gives
someone materially wrong advice.

---

## Stage 4: an absence is checked against the document

`missing_a`, `missing_b` and `missing_both` are the only verdicts in this system that
**assert a negative**. Every other verdict compares two things the model found, and can be
audited by reading the two quotes. A negative has no quote by construction — and model
recall is not 1.0.

We measured it. Two pairs, 34 dimensions, audited by hand against the PDFs' own text:

| Pair | Dimension | Reported | The document actually says |
|---|---|---|---|
| DK Tryg | `territories` | absent from the 2022 document | **Identical clause in both**, under "Hvor er jeg dækket?" |
| IE Aviva/AIG | `foreign_days` | in neither document | Aviva: "Identical cover in the EU for up to **31 days**" |
| IE Aviva/AIG | `excess_conditional` | in neither document | Aviva: "An additional policy excess of **€2,500** applies…" |
| IE Aviva/AIG | `territories` | in neither document | **Both** carry "Where am I covered?" |

**Four of thirty-four wrong — 11.8%.** The pipeline could not tell *the document is
silent* from *we failed to find it*, and presented the second as the first.

`app/absence.py` closes it. Before a `not_found` is allowed to become a finding, the
document's own text is searched for that field's vocabulary and, where the IPID section
*is* the dimension, its mandated heading. A hit demotes the absence to `ambiguous` —
*"the document raises this and does not settle it"* — carrying the line it was found on as
evidence. It **only ever demotes**: it never promotes an absence into a value, never picks
between candidates, never writes a number.

| | Before | After |
|---|---|---|
| DK Tryg 2022 vs 2024 | 1 false of 18 | **0** |
| IE Aviva vs AIG | 3 false of 16 | **1** of 14 |
| Combined | 11.8% | **3.1%** |
| Cost | — | ~0.1s, no model call |

**Caveat, stated plainly: 3.1% is measured on the documents the check was built against.**
A held-out split is the next piece of work, and until it exists the number is a dev-set
number.

Two things were deliberately cut from the check after measuring them:

- **Mandatory section headings as general evidence.** Every IPID carries "When and how do
  I pay?" by regulation, so the heading proves the document is an IPID and nothing else.
  Mapping it to `price.annual_premium` demoted a *true* absence on all four documents.
  Three headings survive, where the section *is* the dimension.
- **Limits borrowing their cover's vocabulary.** "Legal expenses cover" proves legal cover
  is discussed; it says nothing about whether a **limit** is stated, and the amount is the
  thing the reader came for. Those absences now stand. An absence we cannot check stays an
  absence — the conservative direction.

The better outcome is that the honest answer is also the more useful one. "Neither
document discusses roadside assistance" is false and unhelpful. *"Your document names
roadside assistance as one of several optional extras and never says whether you have it
or what it costs"* is true, and it is a better question to put to an insurer.

---

## One quote cannot be evidence for two unrelated claims

`app/validate.py` catches a different failure. On the Tryg pair the model returned the
territory clause as the quote for *two* fields, and the comparison faithfully reported
that European roadside cover had been added at renewal. Nothing had been added.

The first version of this check demoted every field that shared a quote. Measured over
two real pairs it fired six times and was **right once** — the five wrong ones were all
one sentence carrying two related facts:

- `"Fire, theft or attempted theft – loss of or damage to your car"` → fire **and** theft
- `"Identical cover in the EU for up to 31 days"` → the benefit **and** its scope
- `"Selskab: Tryg Forsikring A/S FT-nr.: 53070 Danmark"` → insurer **and** country

It was eating correct values. `vocab.match_all` says as much in its own docstring: one
clause routinely carries a benefit *and* a scope. So the check was narrowed to quotes
stretched **across unrelated subjects**, and the Tryg case it was written for is now
caught where the defect actually lived — in the unverified absence on the other document.

---

## The EU standardisation layer

Under the Insurance Distribution Directive (EU) 2016/97, every non-life insurance product
sold in the EU must carry an **Insurance Product Information Document (IPID)**. Commission
Implementing Regulation (EU) 2017/1469 fixes its presentation format and its nine
sections, in the same order, in every member state and every language:

What is this type of insurance · What is insured · What is not insured · Are there
restrictions on cover · Where am I covered · What are my obligations · When and how do I
pay · When does cover start and end · How do I cancel

The regulation also holds the document to two A4 pages, three at most.

That is a pan-European, legally mandated, deliberately compact common structure — the
backbone that makes cross-border normalisation tractable without building an insurance
ontology from scratch.

**The container is harmonised. Nothing inside it is.** Language, terminology, currency,
number format and national product law all vary, EIOPA confirms manufacturers may build
their own IPIDs, and real documents deviate: the Aviva Ireland motor IPID carries **eight**
sections, not nine, and orders them differently. Section matching is therefore semantic,
never positional. German IPIDs arrive embedded in 40–70 page, 300,000-character policy
packs.

---

## Language, and the 100× error

Local terms map to language-independent canonical keys:

| | | |
|---|---|---|
| `selvrisiko` (DA) | `Selbstbeteiligung` (DE) | `excesses.*` |
| `franchise` (FR) | `eigen risico` (NL) | `excesses.*` |
| `Vejhjælp` (DA) | `Schutzbrief` (DE) | `coverage.roadside_assistance` |
| `Retshjælp` (DA) | `Rechtsschutz` (DE) | `coverage.legal_assistance` |

Number format is market-dependent and cannot be guessed. **`2,500` is two thousand five
hundred in Ireland and two point five in Germany.** `extract()` takes a market code and
refuses to infer one; `app/vocab.py` holds the convention per market. Getting this wrong
is a 100× error in a number a person may act on.

Output is English. Source quotations stay in the original language, always — a translated
quote is no longer evidence.

---

## The corpus

`corpus/register.yaml` tracks 48 published IPIDs across DK, DE, IE, FR and NL, with a
fetch date and a licence note per source. Fourteen are downloaded into `corpus/pdf/`.

**We do not scrape.** A source with no documented machine route is registered as blocked,
with the date it was probed and a drafted contact email in `corpus/contact/`.

The two demo pairs are drawn from it:

| File | Documents | What it shows |
|---|---|---|
| `web/demo-dk.json` | Tryg Forsikring, Denmark, 2022 vs 2024 | 12 of 18 dimensions in neither document, 6 named without a figure |
| `web/demo-ie.json` | Aviva MotorCare vs AIG, Ireland | a €300 excess and a €30,000,000 liability limit — each stated by one insurer only |

Both are **verbatim responses from the live API**, saved. The page replays them through
`buildLive()`, the same function a live upload goes through — not a parallel path — so the
example cannot drift from the product. Open the files.

---

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # add your Nebius Token Factory key

uvicorn app.main:app --reload   # http://localhost:8000
pytest -q                       # 63 tests, no network required
```

The page at `/` is fully usable with no API key: both recorded runs are static files
beside it, so the example works offline and a cold API never blocks a reader.

Configuration lives in `.env`:

```
NEBIUS_API_KEY=...
NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1
KLAUSUL_MODEL_EXTRACT=nvidia/nemotron-3-super-120b-a12b
KLAUSUL_MODEL_EXPLAIN=nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B
```

Deployment: `render.yaml` (Docker, free tier) for the API, `.github/workflows/pages.yml`
for the page. `DEPLOY.md` has the walkthrough. The API key is never committed — `sync:
false` in `render.yaml` makes Render prompt for it.

---

## What it will not do

- Recommend an insurer or tell you to switch. It is decision support, not advice, and not
  regulated intermediation.
- Invent a missing value, or resolve a contradiction silently.
- Present an inference as a stated fact.
- Claim legal certainty about a clause.
- Report an absence it has not checked against the document.

When confidence is low, the answer is *"we could not determine this reliably from the
documents you uploaded"*, plus the question to ask. **That is a successful output.**

---

## Scope

In: PDF upload → extraction → provenance validation → absence verification →
deterministic comparison → personal relevance → evidence → questions to ask. Private
motor, EU/EEA.

Out: insurer search, live quotes, a marketplace, purchasing, broker integration, claims
handling, accounts, other insurance lines, US support.

---

## Layout

```
app/schema.py      canonical model + the Field provenance envelope + comparable dimensions
app/extract.py     PDF -> canonical JSON, with the rules that stop fabrication
app/validate.py    one quote cannot be evidence for two unrelated claims
app/absence.py     an absence is checked against the document before it is reported
app/compare.py     deterministic comparison — contains no model call, by design
app/relevance.py   profile weighting — cannot alter a value or a verdict
app/explain.py     the only model-written prose, called after the comparison is settled
app/vocab.py       local term -> canonical key, and the per-market number conventions
app/main.py        FastAPI
web/index.html     the interface, self-contained
web/demo-*.json    two recorded runs over published IPIDs
corpus/            the source register, the PDFs, and the contact drafts
tests/             63 tests; every fixture is text from a real published IPID
tools/             corpus fetcher (probe-first, never scrapes)
docs/              PRD, setup, pitch notes
```

---

## Status

Hackathon build, and honest about where it is.

- **Works**: extraction, provenance, absence verification, comparison, relevance,
  explanation, both recorded demos, live upload against Nebius Token Factory.
- **Measured**: 3.1% false findings across 32 dimensions — on the documents the check was
  built against. Not yet held out.
- **Weakest**: `coverage_limits.*` dimensions have no vocabulary of their own, so an
  absence there cannot be verified and is left standing. Aviva's "up to 31 days" is the
  known live example.
- **Untested**: France and the Netherlands have registered sources and no downloaded
  documents.

MIT licensed. No account, no storage — documents are read in memory to answer one request
and are not retained.
