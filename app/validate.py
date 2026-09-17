"""One quote, one claim.

The model is asked to return a verbatim quote for every value it reports. Nothing
stops it returning the SAME quote for two different fields, and on the real Tryg pair
it did exactly that: the territory clause

    "Forsikringen gaelder i Europa samt i de lande uden for Europa, der er tilsluttet
     'Groent kort ordningen'"

was cited as evidence both for `territories` and for roadside assistance in the rest of
Europe -- in the 2024 document but not the 2022 one. The comparison engine then did its
job faithfully and reported that European roadside cover had been ADDED at renewal.
Nothing had been added. It is a territory clause.

That failure is invisible to the model (it cannot see its own other answers) and
invisible to the comparison engine (which only sees two values). It is, however,
trivially visible to ordinary code looking at one document's answers side by side --
which is the same argument as compare.py containing no model call.

WHY THIS DOES NOT TRY TO PICK A WINNER
--------------------------------------
The obvious next step is to arbitrate: ask the vocabulary which field the quote really
supports, keep that one, demote the rest. We tried it. On the clause above,
`vocab.match_all` returns {'coverage.foreign_travel'} -- it matches on the word
"Europa" alone -- so arbitration would have kept the artefact and demoted the correct
field. A confident wrong answer, produced by the component whose purpose is to prevent
confident wrong answers.

So this does the honest thing instead. If one sentence is the sole evidence for two
claims, then that sentence settles neither, and both become `ambiguous` with the
conflict named. Refusing to decide is the same stance the product takes everywhere
else: an absence is drawn as an absence, and evidence that does not settle a question
is not promoted into an answer.
"""
from __future__ import annotations

import re
import unicodedata

from .schema import Field, Policy, Status

MIN_QUOTE = 20          # below this a "quote" is a fragment, and fragments repeat innocently


def _norm(text: str) -> str:
    """Fold a quote to its comparable core.

    The same clause appears in the 2022 and 2024 Tryg documents with different
    apostrophes (' vs ''), so punctuation and case cannot be part of the identity.
    """
    s = unicodedata.normalize("NFKD", text.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _walk(p: Policy):
    """Every field in the policy, with the dotted path that names it."""
    for group in ("document", "price"):
        node = getattr(p, group, None)
        if node is None:
            continue
        for name in type(node).model_fields:
            v = getattr(node, name, None)
            if isinstance(v, Field):
                yield f"{group}.{name}", v
    for group in ("coverage", "coverage_limits", "excesses"):
        for name, v in (getattr(p, group, None) or {}).items():
            yield f"{group}.{name}", v
    for group in ("exclusions", "obligations", "claims_conditions"):
        for i, v in enumerate(getattr(p, group, None) or []):
            yield f"{group}[{i}]", v
    for name in ("territories", "foreign_use_limitations", "duration", "cancellation", "no_claims"):
        v = getattr(p, name, None)
        if isinstance(v, Field):
            yield name, v


ASSERTED = (Status.EXPLICIT, Status.INFERRED)


def shared_evidence(policy: Policy) -> list[dict]:
    """Find quotes doing double duty, demote every field that leans on them.

    Mutates the policy. Returns one record per conflict so the caller can show the
    reader what happened rather than quietly changing an answer underneath them.
    """
    by_quote: dict[str, list[tuple[str, Field]]] = {}
    for path, f in _walk(policy):
        if f.status not in ASSERTED or not f.source_text:
            continue
        key = _norm(f.source_text)
        if len(key) < MIN_QUOTE:
            continue
        by_quote.setdefault(key, []).append((path, f))

    conflicts = []
    for key, entries in by_quote.items():
        paths = sorted({p for p, _ in entries})
        if len(paths) < 2:
            continue
        quote = entries[0][1].source_text or ""
        for path, f in entries:
            f.status = Status.AMBIGUOUS
            f.confidence = min(f.confidence, 0.4)
            others = [p for p in paths if p != path]
            f.note = ("the same sentence was returned as evidence for "
                      + ", ".join(others)
                      + " as well, so it does not settle this one on its own")
        conflicts.append({
            "quote": quote,
            "page": entries[0][1].source_page,
            "document": entries[0][1].source_document,
            "fields": paths,
        })
    return conflicts


def conflict_notes(conflicts: list[dict]) -> list[str]:
    """Plain sentences for the uncertainties list the reader actually sees."""
    out = []
    for c in conflicts:
        q = (c["quote"] or "")[:90]
        out.append(
            f"One sentence was used as evidence for {len(c['fields'])} different fields "
            f"({', '.join(c['fields'])}), so none of them is settled by it: »{q}«"
        )
    return out
