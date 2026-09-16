# Klausul

**EU motor insurance, read with its own evidence.**

*Klausul* is Danish, German, Norwegian and Swedish for **clause** — the unit this
product works in. Every figure it shows is a clause, quoted verbatim, with a page
number and a confidence score.

An EU motor-insurance comparison assistant. It converts insurance documents into one
structured model, identifies the material differences, shows the evidence behind every
finding, explains what each difference means for the individual user, and lists what
they should clarify before renewing or switching.

Built for the **Nebius x NVIDIA Global AI Hackathon** · track: Personal AI ·
runs on **Nebius Token Factory** using **NVIDIA Nemotron 3**.

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
| 3. Schema + provenance validation | code | A value with no quote behind it is demoted, not trusted |
| 4. Comparison | **code, no model** | A difference in the output appeared in the documents |
| 5. Relevance weighting | **code, no model** | Circumstances change what matters, never what is true |
| 6. Explanation | **Nemotron 3 Nano** | Only now: what does this confirmed difference mean? |

The model extracts. Code decides. The model then explains what code decided.

---

## Provenance is the schema, not a feature

No bare value ever enters the comparison engine. Every field is this:

```json
"collision_excess": {
  "value": 700,
  "unit": "EUR",
  "status": "explicit",
  "confidence": 0.96,
  "source_document": "Angebot_Meridian.pdf",
  "source_page": 3,
  "source_text": "Selbstbeteiligung Vollkasko: 700 EUR je Schadenfall"
}
```

`source_text` is verbatim and untranslated. Six statuses are possible:

`explicit` · `inferred` · `not_found` · `not_applicable` · `ambiguous` · `conflicting`

**`not_found` never becomes `not covered`.** An absence is reported as an absence, and
turned into a question for the insurer. In consumer insurance that distinction is not a
nicety — silently reading a missing clause as "no cover" is how a comparison tool gives
someone materially wrong advice.

---

## The EU standardisation layer

Under the Insurance Distribution Directive (EU) 2016/97, every non-life insurance
product sold in the EU must carry an **Insurance Product Information Document (IPID)**.
Commission Implementing Regulation (EU) 2017/1469 fixes its presentation format and its
nine sections, in the same order, in every member state and every language:

What is this type of insurance · What is insured · What is not insured · Are there
restrictions on cover · Where am I covered · What are my obligations · When and how do
I pay · When does cover start and end · How do I cancel

The regulation also holds the document to two A4 pages, three at most.

That is a pan-European, legally mandated, deliberately compact common structure — and
it is the backbone that makes cross-border normalisation tractable without building an
insurance ontology from scratch. The IPID is the normalisation target; full contractual
terms usually live in other documents, and the app treats those as additional sources
rather than assuming the IPID is complete.

---

## Language

Local terms map to language-independent canonical keys:

| | | |
|---|---|---|
| `selvrisiko` (DA) | `Selbstbeteiligung` (DE) | `excesses.*` |
| `franchise` (FR) | `eigen risico` (NL) | `excesses.*` |
| `Vejhjælp` (DA) | `Schutzbrief` (DE) | `coverage.roadside_assistance` |
| `Retshjælp` (DA) | `Rechtsschutz` (DE) | `coverage.legal_assistance` |

Output is English. Source quotations stay in the original language, always — a
translated quote is no longer evidence.

---

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # add your Nebius Token Factory key

python tools/make_demo_pdfs.py  # three synthetic policies, IPID-shaped
uvicorn app.main:app --reload   # http://localhost:8000
```

`web/demo.html` also opens standalone with cached extraction fixtures — the demo has no
network dependency, deliberately.

Configuration lives in `.env`:

```
NEBIUS_API_KEY=...
NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1
KLAUSUL_MODEL_EXTRACT=nvidia/nemotron-3-super-120b-a12b
KLAUSUL_MODEL_EXPLAIN=nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B
```

---

## What it will not do

- Recommend an insurer or tell you to switch. It is decision support, not advice, and
  not regulated intermediation.
- Invent a missing value, or resolve a contradiction silently.
- Present an inference as a stated fact.
- Claim legal certainty about a clause.

When confidence is low, the answer is *"we could not determine this reliably from the
documents you uploaded"*, plus the question to ask. That is a successful output.

---

## Scope

In: PDF upload → extraction → normalisation → deterministic comparison → personal
relevance → evidence → questions to ask. Private motor, EU/EEA.

Out: insurer search, live quotes, a marketplace, purchasing, broker integration, claims
handling, accounts, other insurance lines, US support.

---

## Layout

```
app/schema.py      canonical model + the Field provenance envelope + comparable dimensions
app/extract.py     PDF -> canonical JSON, with the rules that stop fabrication
app/compare.py     deterministic comparison — contains no model call, by design
app/relevance.py   profile weighting — cannot alter a value or a verdict
app/explain.py     the only model-written prose, called after the comparison is settled
app/main.py        FastAPI
web/demo.html      the interface
tools/             synthetic demo policy generator
docs/              PRD, setup, pitch notes
```

---

## Status

Hackathon MVP. The demo page ships with cached extraction output so it runs without a
network; the live path calls Nebius. Insurers, documents and figures in `demo/` are
invented and are not any real insurance product.

MIT licensed.
