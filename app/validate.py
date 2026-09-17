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


"""NARROWED, AFTER MEASUREMENT.

The first version demoted every field sharing a quote. Run over two real pairs it fired
six times and was right once. The five wrong ones were all one shape — a single clause
that genuinely carries two related facts:

    "Fire, theft or attempted theft - loss of or damage to your car"
        -> coverage.fire AND coverage.theft. Both true. One sentence, two perils.
    "Identical cover in the EU for up to 31 days"
        -> coverage.foreign_travel AND foreign_use_limitations. The benefit and its scope.
    "Selskab: Tryg Forsikring A/S FT-nr.: 53070 Danmark"
        -> document.insurer AND document.country. Both stated, right there.

vocab.match_all says this outright: "One clause routinely carries a benefit AND a scope
... which is why this returns a set rather than a winner." The validator contradicted the
vocabulary layer sitting next to it, and cost us the Aviva 31-day limit.

So the rule is now: a quote shared WITHIN a family is legitimate double duty and is left
alone; a quote stretched ACROSS families still settles nothing.

The case this was built for — the Tryg territory clause cited for both `territories` and
roadside assistance — falls inside the territory family, so it is no longer caught here.
It does not need to be. The damage was never the shared quote; it was the unverified
ABSENCE on the other document, which app/absence.py now checks directly and which was the
real defect all along."""


def _family(path: str) -> str:
    """The subject a path belongs to. Two paths in one family may share a sentence."""
    if path.startswith("document."):
        return "document"
    if path.startswith("price.") or path in ("duration", "cancellation"):
        return "contract"
    if path in ("territories", "foreign_use_limitations", "coverage.foreign_travel"):
        return "territory"
    if path.startswith("coverage."):
        return "perils"            # one clause listing several perils is normal drafting
    # A cover, its limit and its excess are three readings of one promise, and IPIDs
    # routinely state all three in one line: "replacement vehicle for up to 14 days".
    for group in ("coverage_limits.", "excesses."):
        if path.startswith(group):
            return "cover:" + path[len(group):].split("_")[0]
    return path


def shared_evidence(policy: Policy) -> list[dict]:
    """Find quotes stretched across unrelated subjects; demote the fields that lean on them.

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
        if len({_family(p) for p in paths}) < 2:
            continue                       # one subject, one sentence — normal drafting
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
