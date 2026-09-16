# Accounts and credits — do these yourself, tonight

Three sign-ups. I cannot create accounts or enter card details for you, so these are
the exact steps. Budget fifteen minutes.

---

## 1. Nebius Token Factory — required

The hackathon rules require the project to run on **Nebius Token Factory or Nebius AI
Cloud** and to use **at least one NVIDIA open-source model**.

1. Create the account at **tokenfactory.nebius.com**.
2. It will ask for a billing address or card. This is anti-fraud, not a charge —
   expect a €0 verification hold. Enter it yourself.
3. Profile menu, top right → **Top up** → enter your promo code.
4. Create an API key. Paste it into `.env` as `NEBIUS_API_KEY`.

**Your credits, added up:**

| Source | Amount | Code / route |
|---|---|---|
| Your existing promo email | $50 | `pJYLKJzMqXWbK9GT` — valid until 31 Dec 2027 |
| Devpost hackathon form | $25 | activation code `NEBIUS-DEVPOST-GLOBAL26` |
| Nebius Builders Program | $25 | join the programme |
| Builders & Brews Copenhagen | more | handed out at the event tomorrow |
| | **$100+** | |

Claim the Devpost $25 and the Builders Program $25 **before** tomorrow, so you arrive
already provisioned rather than queuing for a code.

**Models to set:**

```
KLAUSUL_MODEL_EXTRACT=nvidia/nemotron-3-super-120b-a12b
KLAUSUL_MODEL_EXPLAIN=nvidia/nemotron-3-nano-30b-a3b
```

Nemotron 3 Nano Omni is the multimodal one — that is the route for scanned PDFs if you
get that far. Check the exact IDs in the Token Factory model catalogue when you sign in;
they can change.

---

## 2. Tavily — the second platform

Tavily co-hosts the event and has its own **$3,000 "Best use of Tavily"** prize.

1. Sign up at **tavily.com**. The free tier is 1,000 API credits, no card.
2. `TAVILY_API_KEY` into `.env`.
3. More credits handed out at the event.

**Do not bolt it on.** There is one honest use in Klausul: when an uploaded document
*references* another document the user does not have — the Meridian offer in the demo
points at a `Leistungsübersicht` that was never uploaded — Tavily can look up whether
the insurer publishes those terms publicly, and the row moves from `not_found` to
`found_externally`, clearly labelled as a different evidence class from the user's own
documents. That is a real feature, not a sponsor tax. If you build it, that provenance
distinction is what wins the category.

---

## 3. Supabase — optional

Also at the event, also giving credits. Only worth it if you add saved comparisons or
accounts. The MVP scope says no account system, so take the credits and decide later.

---

## 4. Devpost

Register on the hackathon page itself so you are in the entrant list. Nothing has to
be submitted yet.

---

## Running the code

```bash
python -m venv .venv && .venv\Scripts\activate     # Windows
pip install -r requirements.txt
copy .env.example .env                              # then paste your keys in

python -m app.cli demo/Fornyelse_2026.pdf           # single extraction, live on Nebius
uvicorn app.main:app --reload                       # the API
```

The demo page in `web/demo.html` runs standalone with cached fixtures and needs no
network. That is deliberate: venue wifi is not a dependency of your demo.

---

## The submission checklist — due 30 October, 10:00 PDT

You are inside the submission window already (it opened 26 August), so nothing here
needs to be held back or timed.

- [ ] Working app that runs on Nebius Token Factory
- [ ] Uses at least one NVIDIA open-source model — Nemotron 3
- [ ] Public repo with an **MIT LICENSE file visible at the top level**
- [ ] README with setup instructions
- [ ] Working demo URL
- [ ] Demo video, **3 minutes maximum**, on YouTube
- [ ] Track selected — **Personal AI** is the better fit than Best Apps and Agents
- [ ] Feedback on Nebius/NVIDIA tools submitted (there are ten $100 awards for this,
      and it is the cheapest thing on this list)
