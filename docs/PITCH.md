# Tomorrow — Builders & Brews Copenhagen

**Gdanskgade 2, 2150 København · Tuesday 16 September · Hosts: Nebius + Tavily, with Milo AI, AI Founders Network, Supabase**

Read this once on the way there. It is not a script to recite.

---

## 1. What this event actually is

It is a **hands-on build day**, not a pitch competition. The page says plainly:
*"no requirement to submit a project or present your work."* There is no stage, no
2–5 minute slot, no judges in the room.

That changes the unit of attention. You are not pitching for minutes — you are having
conversations of roughly **thirty seconds each**, and the question is whether the other
person asks a second question.

Two people are worth knowing by name:

| Who | Role | What they care about |
|---|---|---|
| **Jacquie Capur** | Senior Developer Advocate, Nebius | Who is actually building on Token Factory, and what breaks |
| **Evan Rimer** | Forward Deployed Engineer, Tavily | Where search genuinely belongs in an agent, not where it is bolted on |

A developer advocate's job is to find builders worth pointing at. That is literally
the outcome you asked for. You do not have to engineer it — you have to be the
person who is already running.

---

## 2. The thirty seconds

Lead with the technical thesis, not the consumer story. This room is engineers.

> "Every EU insurance renewal is a document you can't compare to last year's.
> I'm building the thing that reads both and tells you what actually changed.
>
> The interesting part isn't the diff. **The model is never allowed to decide which
> policy is better.** It only extracts fields — each one with a verbatim quote, a page
> number and a confidence score. Plain code does the comparison. So when it says
> *'European roadside assistance could not be confirmed'*, that's a real answer, not
> a hallucination.
>
> It's on Nemotron via Token Factory, because the documents are in six languages and
> the extraction has to hold in all of them."

**The eight-second version**, if someone is half-listening:

> "Insurance documents in, evidence-bound comparison out. The model extracts; code decides."

Then stop talking and open the demo.

---

## 3. The demo, in the order that lands

You have a private page you can open on your phone. **Share it first** — open the
artifact's share menu, or nobody else can load the link you send them.

Three beats, about forty seconds:

1. **The headline sentence.** Not "6 changes" — *"one change that could not be
   confirmed, and it matters more than the €90 price rise."* The product leads with a
   judgement about relevance, not a count.
2. **Tap the roadside row.** Fact / What it means / For you, visually separated, with
   the Danish source quote and page number underneath. Say: *"the quote is verbatim
   and untranslated — that's the audit trail."*
3. **Flip the "weight by my circumstances" toggle.** The order of the rows changes.
   The numbers do not. Say: *"personalisation moves relevance. It never touches a
   fact. That separation is the whole architecture."*

Beat 3 is the one they will remember. Do not rush to it — but do not skip it.

---

## 4. The three questions you will get, and the answers

**"Isn't this just PDF diffing?"**
> No — a diff compares text. This normalises two documents written in different
> languages by different insurers into one schema, and then compares *fields*.
> The EU already standardised the source document: the IPID, under Implementing
> Regulation 2017/1469. That regulation is the backbone most people don't know exists.

**"How do you know the extraction is right?"**
> I don't assume it. Every field carries a status — explicit, inferred, not_found,
> ambiguous, conflicting — plus a quote and a page. A value with no quote behind it is
> automatically demoted. And "not found" is never converted to "not covered", which is
> the failure mode that would make the product dangerous.

**"Why Nemotron and not a frontier model?"**
> Two reasons, and one of them is not credits. The documents are multilingual and long,
> which is what Nemotron 3 is built for; and the whole thing has to be open source and
> reproducible by someone else, which rules out a closed model. Super for extraction,
> Nano for the explanation layer.

---

## 5. Ask them something

This is the actual positioning move. At a build day, the person who asks the developer
advocate a sharp question is the person remembered — far more than the person who
delivers a smooth pitch.

Pick one or two. Don't run the list.

**For Jacquie (Nebius):**
- How reliable is constrained JSON output on Nemotron 3 Super for long multilingual
  documents? Is there a schema-enforcement path, or is it prompt-level only?
- Does Token Factory expose logprobs? I'm using self-reported confidence and I'd rather
  calibrate it against something real.
- For scanned PDFs — is Nemotron 3 Nano Omni the right route, or should OCR stay separate?

**For Evan (Tavily):**
- My documents are uploaded, not searched. Is there an honest role for Tavily here —
  resolving an insurer's public terms when the user's own document references an annex
  they don't have?

That last question is worth asking out loud even if the answer is no. It shows you
won't bolt a sponsor's tool on for the sake of a prize category — which is exactly the
judgement that makes an advocate trust you.

---

## 6. What not to lead with

- **Not the CSO years.** At a build day, opening with fifteen years of executive
  experience reads as consultant, not builder, and the room discounts it. Lead with the
  thing that is running. Let the background arrive second, when they ask what you do.
- **Not the book, not the brand.** Attribution is a fact; positioning is a claim.
- **Not the prize.** Everyone there knows about the prize.

The one line of background that does land, if it comes up naturally:

> "I've built this evidence-bound extraction pattern three times in industry now.
> This is the open version of it."

That is true, it is checkable, and it separates you from the room without a single
adjective.

---

## 7. Practical

- **Charge your phone.** The demo is the pitch.
- **No printer needed.** The leave-behind is the link — share the artifact, then send
  it in the moment. A link someone opens while standing next to you beats paper.
- **Collect credits.** Tavily, Token Factory and Supabase credits are handed out at the
  event. Ask for all three.
- **Get two names, not twenty.** One conversation you follow up on Wednesday is worth
  more than a room full of handshakes.
