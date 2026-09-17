# Devpost submission — copy/paste

Track: **Best Apps and Agents**

---

## Elevator pitch (200 characters max)

> Two insurance documents in. What differs, what neither one settles, and the exact
> sentence behind every finding. The model extracts; code decides.

*(139 characters.)*

---

## Project description

### Inspiration

I set out to build a renewal-comparison tool for EU car insurance, then collected the
documents it would have to read. Fourteen published Insurance Product Information
Documents, from Denmark, Germany and Ireland.

**One of them states an excess amount.** The Danish ones contain no money figures at all.
A real Tryg renewal pair — 2022 against 2024 — is 94% identical text with nothing to
compare: no premium, no excess, no limits.

My original demo showed a Danish theft excess moving from €300 to €500. That document
format does not exist. I had invented it.

So I kept the product and changed the claim. The finding is not usually *"this number
moved."* It is *"the document names the cover and never gives you the number."* An IPID
describes the product; your premium and your excess live on the policy schedule, which is
a different document, and nobody compares it.

That is the gap the tool now shows you.

### What it does

Upload two insurance PDFs and pick your market. Klausul:

- extracts both into one canonical model, with a **verbatim quote, page number and
  confidence score on every single value**;
- verifies every reported absence against the document's own text before it is allowed to
  become a finding;
- compares the two **in ordinary code, with no model involved**;
- orders findings by what your circumstances make relevant, without ever changing what is
  true;
- explains each confirmed difference in plain language;
- ends with questions to send your insurer, generated only from what the documents left
  open.

It never recommends an insurer. It is decision support, not advice.

### How I built it

Extraction runs **Nemotron 3 Super (120B)** on **Nebius Token Factory** — six languages,
one schema, long documents. Explanation runs **Nemotron 3 Nano (30B)** on the same
endpoint, and is only ever called *after* a difference has been confirmed by code.

The pipeline is deliberately split:

| Stage | Who | Why |
|---|---|---|
| Text + page map | `pdfplumber` | page numbers must survive, or citation is impossible |
| Extract | **Nemotron 3 Super** | six languages, one schema |
| Provenance validation | code | a value with no quote behind it is demoted |
| **Absence verification** | **code** | a negative from one model pass is unverified |
| Comparison | **code** | a difference in the output appeared in the documents |
| Relevance weighting | **code** | circumstances change what matters, never what is true |
| Explanation | **Nemotron 3 Nano** | what does this *confirmed* difference mean? |

`app/compare.py` contains no model call. That is the product, not an optimisation.

FastAPI, Docker on Render, static page on GitHub Pages so a cold API never blocks a
reader. 63 tests, no network required.

### Challenges

**The model's silence is not the document's silence.** `missing_a` / `missing_b` /
`missing_both` are the only verdicts in the system that assert a *negative* — every other
verdict compares two things the model found and can be audited by reading two quotes. A
negative has no quote by construction, and recall is not 1.0.

I audited 34 dimensions across two real pairs by hand against the PDFs. **Four were
wrong**, all the same shape: the model missed a clause, and the tool reported it as absent
— a finding about someone's insurance, produced by a failure to read.

The fix uses no model call. Before a `not_found` becomes a finding, the document's own
text is searched for that field's vocabulary — and, where an IPID section *is* the
dimension, its mandated heading. A hit demotes the absence to *"the document raises this
and does not settle it"*, carrying the line it was found on. It can only ever **demote**,
never promote, so it cannot introduce a confident wrong answer.

**11.8% → 3.1% false findings. Zero on the Danish pair. Cost: 0.1 seconds, no model call.**

Two things I cut after measuring them:

- Mandatory section headings as general evidence. Every IPID carries "When and how do I
  pay?" by regulation, so it proves nothing about the premium — mapping it that way
  demoted a *true* absence on all four documents.
- Limits borrowing their cover's vocabulary. "Legal expenses cover" proves legal cover is
  discussed; it says nothing about whether a **limit** is stated, and the amount is the
  thing the reader came for.

An earlier guard had the same disease in reverse: it demoted any field sharing a quote
with another. Measured, it fired six times and was **right once** — "Fire, theft or
attempted theft" is one sentence about two perils, and the guard was eating correct
values. Narrowed to quotes stretched across *unrelated* subjects.

### Accomplishments

Every number in the demo is traceable to a line in a PDF anyone can download. The two
recorded runs shipped with the page are **verbatim API responses**, replayed through the
same function a live upload goes through — so the example cannot drift from the product.

And the measurement exists. The honest failure rate is published in the README, with its
caveat attached.

### What I learned

A fix verified at the unit level is not verified. The false finding I was chasing needed
*three* fixes, not the two I thought — the validator, the comparison precedence, and then
the presentation layer, which was restating the same false claim in a different wrapper. I
only found the third by rendering the page and reading it.

And the honest answer is often the more useful one. *"Neither document discusses roadside
assistance"* is false and useless. *"Your document names roadside assistance as one of
several optional extras and never says whether you have it"* is true, and it is a better
question to put to an insurer.

### What's next

- A held-out document split, so 3.1% stops being a development-set number.
- Vocabulary for the `coverage_limits.*` dimensions, the one class of absence that
  currently cannot be verified.
- France and the Netherlands: registered sources, no documents yet.
- The same shape generalises. A regulator mandates a document to make something
  comparable, and the document discloses the inputs and stops one step short of the number
  that decides — PRIIPs KIDs, bank Fee Information Documents, telecom contract summaries,
  ESIS mortgage sheets. Same pipeline, different vocabulary.

### Built with

`python` · `fastapi` · `pdfplumber` · `pydantic` · `nebius-token-factory` ·
`nvidia-nemotron-3-super-120b` · `nvidia-nemotron-3-nano-30b` · `docker` · `render` ·
`github-pages` · `html` · `css` · `javascript`

---

## Links to submit

| Field | Value |
|---|---|
| Try it out | `https://exploreandreconnect.github.io/klausul/` |
| Repository | `https://github.com/ExploreandReconnect/klausul` |
| Video | *(YouTube URL — public)* |
| API health | `https://klausul-api.onrender.com/health` |

---

## Pre-existing work disclosure

None. Built entirely within the submission period.

---

## Tool feedback — Nebius & NVIDIA

*(Devpost asks for this separately; ten $100 awards attached. Honest and specific beats
enthusiastic.)*

**Nebius Token Factory**

- The OpenAI-compatible endpoint meant zero integration work — one base URL change and the
  existing client worked. That is the right default.
- **Model IDs are case-sensitive and the casing is not guessable.**
  `nvidia/nemotron-3-super-120b-a12b` is lower-case;
  `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` is not. I lost an hour to this and only resolved
  it by listing models over the API. A 404 that echoed the closest match, or documentation
  that showed exact IDs in a copyable block, would have saved it.
- A 502 with no body when a request exceeds the time budget was hard to distinguish from a
  platform fault. An error body naming the cause would help.
- Cold-start and throughput were fine throughout. Two 2-page documents extract
  concurrently in 57–145 seconds on Super.

**NVIDIA Nemotron 3 Super (120B) — extraction**

- Strong at multilingual structured extraction. Danish, German and Irish-English documents
  into one schema, with verbatim untranslated quotes preserved, worked well.
- **`detailed thinking off` in the system prompt was essential.** Without it the model
  spent its token budget deliberating and returned truncated JSON; with it, output was
  clean and roughly 3× faster. This is high-value and under-documented — it deserves to be
  in the first code sample a developer sees.
- Recall on absent fields is the real limitation, and it is not visible without a
  ground-truth audit: the model silently omits a field it missed, which is
  indistinguishable from a field that is not there. **A per-field "I looked and did not
  find it" signal, distinct from omission, would be genuinely valuable** for any
  extraction task where absence carries meaning.
- It returned the same quote as evidence for two different fields without flagging the
  reuse. Understandable — it cannot see its own other answers — but worth documenting as a
  known failure mode for schema-wide extraction.

**NVIDIA Nemotron 3 Nano (30B) — explanation**

- Fast and appropriate for short, bounded, per-finding prose.
- Needed a larger `max_tokens` than expected (3000–4000, not 900) before failures stopped;
  below that it truncated mid-sentence and the JSON never closed. The failure looked like a
  parse error rather than a budget error, which sent me down the wrong path for a while.
- Reliably respected per-field framing instructions once given explicitly — without them it
  would assume a claim scenario for fields that had nothing to do with claims.
