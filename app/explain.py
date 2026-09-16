"""The explanation layer.

This is the only place a language model writes user-facing prose, and it is called
AFTER the comparison is settled. It is given a confirmed difference and asked what
it means. It is not given the option to disagree about what the difference is.
"""
from __future__ import annotations

import json

from pydantic import BaseModel

from .nebius import MODEL_EXPLAIN, complete_json
from .relevance import Weighted

SYSTEM = """You write three short paragraphs about one confirmed difference between two
European motor-insurance policies. You are a translator of findings, not an analyst.

You receive the difference as settled fact. Do not re-open it, re-rank it, or question it.

Return JSON: {"fact": "...", "meaning": "...", "for_you": "..."}

fact     — restate the difference in one plain sentence with the numbers. No interpretation.
meaning  — what it would mean in practice if the user had a claim. One or two sentences.
for_you  — why it matters more or less GIVEN the user's stated circumstances, which are
           supplied to you. Reference the circumstance explicitly. If no circumstance
           applies, say the difference is not especially relevant to this user and why.

Hard rules:
- Never recommend a policy, an insurer, or a switch. You describe; the user decides.
- Never state that something is not covered because it was not found. If the status is
  not_found, say the documents do not settle it and that it needs to be confirmed.
- No hedging filler, no apologies, no "it is important to note".
- Currency as given. Never invent a figure that is not in the input.
- Address the reader as "you". Never "the user", never the third person.
- The input contains a field called `direction`, computed by ordinary code from the two
  documents. It is not an opinion and you may not contradict it. If it says a figure rose,
  every sentence you write must agree that it rose. A model that described an €810 premium
  as "lower" than €720 is the specific failure this rule exists to prevent.
- `user_circumstances` is what the reader actually told us, at the precision they gave.
  Repeat it at that precision. If it says "under 10,000 km a year", never write "8,000 km"."""


class Explanation(BaseModel):
    key: str
    fact: str
    meaning: str
    for_you: str


def _direction(d) -> str:
    """One unambiguous sentence about which way the figure moved, computed here rather
    than left to the model to infer from two numbers. The 30B model read 720 -> 810 as a
    fall and wrote "you would pay 90 less"; the numbers were right there and it still
    got the sign wrong. Deterministic facts belong in deterministic code."""
    a, b = d.a.value, d.b.value
    if not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
        return (f"{d.label}: no single figure on both sides. Verdict from the comparison "
                f"engine: {d.verdict}. Describe only what the quotes support.")
    unit = d.unit or ""
    if b > a:
        way, who = "ROSE", ("worse for the reader" if d.verdict == "better_a"
                            else "better for the reader" if d.verdict == "better_b"
                            else "direction of benefit not rankable")
    elif b < a:
        way, who = "FELL", ("better for the reader" if d.verdict == "better_b"
                            else "worse for the reader" if d.verdict == "better_a"
                            else "direction of benefit not rankable")
    else:
        return f"{d.label} is UNCHANGED at {a} {unit}. Say so plainly."
    return (f"{d.label} {way} from {a} {unit} to {b} {unit} "
            f"(a change of {abs(b - a)} {unit}). This is {who}. "
            f"Every sentence you write must agree that it {way.lower()}.")


def explain_one(w: Weighted, profile_text: str, *, model: str = MODEL_EXPLAIN) -> Explanation:
    d = w.difference
    payload = {
        "direction": _direction(d),
        "label": d.label,
        "verdict": d.verdict,
        "relevance": w.relevance,
        "why_relevant": w.reasons,
        "unit": d.unit,
        "delta": d.delta_text,
        "current": {"value": d.a.value, "status": d.a.status, "quote": d.a.source_text,
                    "page": d.a.source_page, "document": d.a.source_document},
        "other": {"value": d.b.value, "status": d.b.status, "quote": d.b.source_text,
                  "page": d.b.source_page, "document": d.b.source_document},
        "user_circumstances": profile_text,
    }
    raw = complete_json(SYSTEM, json.dumps(payload, ensure_ascii=False, default=str),
                        model=model, max_tokens=900)
    return Explanation(
        key=d.key,
        fact=raw.get("fact", ""),
        meaning=raw.get("meaning", ""),
        for_you=raw.get("for_you", ""),
    )


ACTIONS_SYSTEM = """You write the questions a consumer should ask their insurer before
renewing or switching. Input is a list of differences that are unresolved or material.

Return JSON: {"actions":[{"question":"...","why":"..."}]}

At most five. Ordered by how much they would change the decision.
Every question must trace to a specific unresolved or material item in the input —
never a generic insurance tip. `why` names the gap in one sentence.
Never tell the user what to decide."""


def actions(weighted: list[Weighted], profile_text: str, *, model: str = MODEL_EXPLAIN) -> list[dict]:
    items = [
        {"label": w.difference.label, "verdict": w.difference.verdict,
         "relevance": w.relevance, "delta": w.difference.delta_text,
         "status_current": w.difference.a.status, "status_other": w.difference.b.status}
        for w in weighted
        if w.relevance in ("HIGH", "MEDIUM")
    ][:8]
    raw = complete_json(
        ACTIONS_SYSTEM,
        json.dumps({"differences": items, "user_circumstances": profile_text},
                   ensure_ascii=False, default=str),
        model=model, max_tokens=900,
    )
    return raw.get("actions", [])[:5]
