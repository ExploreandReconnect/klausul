# Klausul — development log

Submission deadline: **30 October 2026, 10:00 PDT (18:00 CET)**
Track: **Personal AI** · Runs on Nebius Token Factory · NVIDIA Nemotron 3

---

## Shipped

| Date | What | Notes |
|---|---|---|
| 15 Sep | Repo scaffold, MIT licence, README, PRD | 23 files |
| 15 Sep | Extraction pipeline (`extract` → `compare` → `relevance` → `explain`) | `compare.py` contains no model call, by design |
| 15 Sep | Canonical schema with the `Field` provenance envelope | 6 statuses; a value with no quote is auto-demoted |
| 15 Sep | Three synthetic IPID-shaped policies, DA + DE | `tools/make_demo_pdfs.py` |
| 15 Sep | FastAPI surface, CLI probe | `POST /compare`, `python -m app.cli` |
| 15 Sep | Design direction scan — 8 products, live style probe | `web/directions.html` |
| 15 Sep | UI direction A ("Nordic Letter") chosen and built | 3 rejected attempts before it |
| 15 Sep | Boundary device: what you carry vs what they carry | Ghost = comparison position |
| 15 Sep | Mobile fixes, bar animation, click-to-evidence, a11y, table view, print CSS | Tier 1 |
| 15 Sep | Copy pass — prose cut 694 → 465 words | Legend absorbed the chart explanation |
| 15 Sep | **Flow B — compare an alternative offer** | Same device, ghost = your policy today |
| 15 Sep | **Corpus apparatus** — register, fetch harness, label sheet, scorer | 31 sources, 2 routes confirmed open |
| 15 Sep | **`app/vocab.py`** — the vocabulary layer | 5 languages, 9 sections, 22 fields, 100 term-language pairs |
| 15 Sep | Market-aware number parsing | `"2,500"` = 2500.0 in IE, 2.5 in DE |
| 15 Sep | Two schema/prompt fixes forced by real documents | Semantic sections; conditional amounts |
| 15 Sep | First tests — 23, passing | `tests/test_vocab.py`, `tests/test_compare.py` |
| 15 Sep | `render.yaml` deploy blueprint | Frankfurt region, key via dashboard |

### Flow B, as built
- Mode switch under the masthead, letter-style (two words and a rule)
- Ghost line relabelled `now`; legend entry becomes "Your policy now"
- Geography strip — the boundary applied to **space** instead of money; Switzerland + UK goes fully dark ("no cover")
- New mark: **dashed green** = given back but *conditional* (the €0 glass excess applies only to a repair)
- Tally reframed to the trade: `−€126` / `+€300` / `2.4 yrs to break even`
- The break-even is stated and then handed back: *"the documents cannot tell you your rate. Only you can."*
- Second "hole": the offer references a `Leistungsübersicht` that was never uploaded

---

## Remaining

Ordered by what gets more expensive the longer it waits.

| # | Item | Why it matters | Est. | Risk if skipped |
|---|---|---|---|---|
| 1a | **Probe the 29 unconfirmed routes** — `python tools/fetch_corpus.py --probe` | Apparatus is built; the routes are unverified. Yours to run: it fetches from your machine against your own documented routes | 1 h | **High** |
| 1b | **Send the contact emails** the blocked entries generate | The rule requires it, and a blocked source is a task not a silence | 30 min | Medium |
| 1c | **Label 30 documents × 18 fields** | `--make-labels`, then fill the sheet. This is the actual constraint — about 5 h, in a language you read | 5 h | **High** |
| 2 | **Score it** — `python tools/score_extraction.py` | Turns ≥90% into a fact. Prints the verdict breakdown, per-market split and weakest fields | 1 h | High |
| 3 | **Wire the UI to the live pipeline** | Today the page runs on baked-in data; `app/` runs live but nothing connects them | ½ day | **High.** "Working demo URL" is a submission requirement |
| 4 | **Upload screen + the two entry choices** | There is no way into the product | ½ day | High |
| 5 | **Profile questions (5–7) + toggle** | Relevance is currently written into the copy, not computed. `relevance.py` exists and is unused by the UI | ½ day | Medium — it's the best demo beat |
| 6 | **Deploy** somewhere public | Submission needs a URL | 2 h | **High** |
| 7 | **3-minute video** | Open on click-to-evidence, not the upload screen | 3 h | **High** — required |
| 8 | **Nebius/NVIDIA tool feedback** | Ten $100 awards; cheapest item on the list | 30 min | Low |
| 9 | Danish / English toggle | Proves the multilingual claim viscerally | 1 h | Low |
| 10 | Tavily: resolve a referenced-but-missing annex | Honest use, own $3,000 category | 3 h | Low |
| 11 | ~~Tests~~ | 23 passing. Extend to `extract`/`explain` once the corpus exists | — | Done (partial) |

---

## Known residuals

Carried openly rather than quietly.

- **The demo page is not live.** It renders cached extraction output. Deliberate — the venue-wifi hedge — but item 3 must land before submission, and the page should then show which mode it is in.
- **`demo/fixtures/` is empty.** `extract.load_fixture()` has no files to load.
- **Extraction prompts are untested.** Zero real documents have been through `extract.py`.
- **Tests cover `vocab` and `compare` only.** Nothing tests `extract`, `explain` or the API — those need the corpus and a live key.
- **Every non-English vocabulary term is unverified.** 8 of 45 section-language pairs confirmed, 0 of 100 field-language pairs. `app/vocab.verification_state()` reports the gap.
- **29 of 31 corpus routes unprobed.** No documents downloaded, nothing labelled, no measured accuracy.
- **`relevance.py` is dead code** from the UI's perspective — the weighting rules exist but the page hard-codes its ordering.
- **No error states.** Upload failures, unreadable PDFs, scanned documents — none handled in the UI.
- **Scanned PDFs unsupported.** `read_pdf` raises on a document with no text layer. Route: Nemotron 3 Nano Omni.
- **Confidence is self-reported** by the model, not calibrated against anything.

---

## Open decisions

| Question | Status |
|---|---|
| Does the €126-vs-€300 break-even belong in Flow B's tally, or is it too close to advice? | **Kept.** It is arithmetic on two stated figures, and the page hands the rate back to the user |
| Time axis (30 days) alongside a money axis (€800) — alarming or accurate? | **Accurate. Leave it.** Decided 15 Sep |
| Where does the premium sit? | **Outside the picture.** It is what they charge, not what you carry |
| Should the repo headline be the method or the product? | **The method.** Insurance is the demonstration |
| Which markets, given the IPID is harmonised? | **DK + DE + IE.** The container is harmonised, the contents are not. Three markets chosen so no two test the same failure mode; FR + NL as a vocabulary-table extension |
| Build the profile toggle next? | **No.** Four submission gates are unmet; the toggle improves the criterion already strongest. Deferred behind the corpus |

---

## Submission checklist — 30 October

- [x] Uses an NVIDIA open model (Nemotron 3 Super + Nano)
- [x] Public repo with a detectable MIT LICENSE at top level
- [x] README with setup instructions
- [x] Both flows built
- [ ] Runs live on Nebius Token Factory end to end
- [ ] Working demo URL
- [ ] Demo video, ≤3 minutes, on YouTube
- [ ] Track selected (Personal AI)
- [ ] Nebius/NVIDIA tool feedback submitted
