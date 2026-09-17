# Demo video — 3:00 script

Devpost requires: **3 minutes or shorter, public YouTube, with audio, showing the project
working, covering how Nebius Token Factory and NVIDIA Nemotron were used.**

Narration is **430 words ≈ 2:52 at 150 wpm.** Read it slower than feels natural. Do not
add anything; if you go over, cut from Act 4, not Act 1.

Nebius and Nemotron are named in Act 2 (0:38) and again in Act 3 (1:22) — early enough
that a judge who stops at ninety seconds has already heard both.

---

## Act 1 — The falsification (0:00 – 0:32)

**On screen:** A real Danish IPID, `dk-tryg-current.pdf`, open and scrolling. No UI yet.
Then a hard cut to the entry page headline: *"Know what your documents don't say."*

> This is a Danish car insurance document. Two pages. It is the standard disclosure the
> EU requires every insurer to give you.
>
> It does not contain your premium. It does not contain your excess. It names roadside
> assistance as an optional extra and never tells you whether you have it.
>
> I built a tool to compare these documents. Then I collected fourteen of them, from four
> countries. **One states an excess amount.** The Danish ones contain no money at all.
>
> So I changed the product. The finding is not "this number moved." The finding is that
> the number was never there.

---

## Act 2 — It working (0:32 – 1:05)

**On screen:** Drag two PDFs onto the upload panel. The waiting screen walking the nine
IPID sections. Then the Danish result page, scrolling slowly through the six
"Stated, but not settled" rows with their Danish quotes.

> Klausul takes two insurance documents. Extraction runs on **Nebius Token Factory**,
> using **NVIDIA's Nemotron 3 Super** — a hundred and twenty billion parameter open model
> — because these documents are Danish, German, Irish, and the terminology is different in
> each one.
>
> Here is the real Tryg pair, 2022 against 2024. Twelve of eighteen things worth comparing
> are in neither document. Six are named without a figure — and the page shows you the
> exact Danish sentence, with the page number.
>
> *Optional extras — for example, roadside assistance.* That is the whole disclosure.

---

## Act 3 — The architecture (1:05 – 1:40)

**On screen:** `app/compare.py` in an editor, scrolled to the top docstring. Then the
pipeline table from the README.

> One design decision matters more than the rest. **The model is never asked which policy
> is better.**
>
> A model asked to rank two policies will produce a confident ranking whether or not the
> documents support one. So the model only extracts, with a verbatim quote and a page
> number for every value. Ordinary code does the comparison — `compare.py` contains no
> model call, by design.
>
> Only after a difference is confirmed does a second model, **Nemotron 3 Nano on Nebius**,
> explain what it means for you. It explains a finding. It never produces one.

---

## Act 4 — What went wrong, and the fix (1:40 – 2:30)

**On screen:** The two Tryg PDFs side by side, both scrolled to *"Hvor er jeg dækket?"*,
with the identical clause highlighted in each. Then the README measurement table.

> Here is a mistake it made. The model read this clause in the 2024 document and missed it
> in the 2022 one. So the tool reported it as **absent** — a finding about your insurance,
> from a failure to read.
>
> Four of thirty-four findings were wrong that way. Twelve per cent.
>
> The fix takes no model call. Before the tool says *"this document doesn't mention it"*,
> it searches that document's own text for the words. Found — then it isn't absent, it's
> unsettled, and it shows you the line. **It can only ever demote a claim, never promote
> one.**
>
> Twelve per cent to three. Zero on the Danish pair. That number is measured on the
> documents I tuned against, so treat it as a development-set number until I hold a set
> out.

---

## Act 5 — Close (2:30 – 3:00)

**On screen:** The Irish tab — €300 and €30,000,000 drawn as solid bars with *"AIG states
none"* beside them. Then the question list, then the repo.

> The Irish pair is the other half. Aviva states a three hundred euro excess; AIG says only
> *"an excess will apply, see your policy schedule."* Those are different facts, and only
> one of them can be compared.
>
> Every finding ends in a question you can send your insurer, generated only from what your
> documents left open.
>
> No account. Nothing stored. Open source, MIT. Both demo runs in the repo are real API
> responses you can open and check.
>
> **An absence is drawn as an absence.**

---

## Recording notes

- **Screen**: 1280 × 800, browser zoom 100%, hide bookmarks bar and extensions.
- **Audio**: record narration separately, in one take per act, then lay it over. Phone
  earbuds in a small room beat a laptop mic in a big one.
- **Pace**: the page has motion of its own — the bars animate in. Let a beat land before
  you scroll.
- **Do not** speed up footage under narration; it reads as padding.
- Upload as **public** (not unlisted — Devpost's rule says public).
- Title: `Klausul — what your insurance documents don't say | Nebius x NVIDIA Global AI Hackathon`
- Put the repo and live URLs in the description.
