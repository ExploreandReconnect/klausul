"""Deterministic comparison engine.

No language model is involved in this file, and that is the point. The model
extracts; this code decides. A difference that appears in the output appeared in
the documents.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from .schema import DIMENSIONS, Dimension, Field, Policy, Status

Verdict = Literal[
    "same", "better_a", "better_b",
    "different_not_rankable", "missing_a", "missing_b", "missing_both",
    "uncertain",
]


class Difference(BaseModel):
    key: str
    label: str
    verdict: Verdict
    a: Field
    b: Field
    delta: float | None = None
    delta_text: str | None = None
    unit: str | None = None
    rankable: bool = True

    @property
    def material(self) -> bool:
        return self.verdict != "same"


def _num(f: Field) -> float | None:
    if not f.usable:
        return None
    try:
        return float(f.value)
    except (TypeError, ValueError):
        return None


def _fmt(v: float, unit: str | None) -> str:
    if unit == "EUR":
        return f"€{v:,.0f}"
    if unit == "days":
        return f"{v:.0f} days"
    return f"{v:g}"


def compare_dimension(a: Policy, b: Policy, dim: Dimension) -> Difference:
    fa, fb = a.get(dim.path), b.get(dim.path)
    base = dict(key=dim.key, label=dim.label, a=fa, b=fb, unit=dim.unit,
                rankable=dim.direction != "not_rankable")

    # Absence is reported as absence. It is never resolved into a value.
    if fa.status is Status.NOT_FOUND and fb.status is Status.NOT_FOUND:
        return Difference(verdict="missing_both", **base)
    if fa.status is Status.NOT_FOUND:
        return Difference(verdict="missing_a", **base)
    if fb.status is Status.NOT_FOUND:
        return Difference(verdict="missing_b", **base)
    if Status.AMBIGUOUS in (fa.status, fb.status) or Status.CONFLICTING in (fa.status, fb.status):
        return Difference(verdict="uncertain", **base)
    if min(fa.confidence, fb.confidence) < 0.60:
        return Difference(verdict="uncertain", **base)

    if dim.direction == "presence_is_better":
        pa, pb = bool(fa.value), bool(fb.value)
        if pa == pb:
            return Difference(verdict="same", **base)
        return Difference(verdict="better_a" if pa else "better_b", **base)

    if dim.direction == "not_rankable":
        same = str(fa.value).strip().casefold() == str(fb.value).strip().casefold()
        return Difference(verdict="same" if same else "different_not_rankable", **base)

    na, nb = _num(fa), _num(fb)
    if na is None or nb is None:
        return Difference(verdict="uncertain", **base)
    if na == nb:
        return Difference(verdict="same", **base)

    delta = nb - na
    sign = "+" if delta > 0 else "−"
    delta_text = f"{sign}{_fmt(abs(delta), dim.unit)}"
    if dim.direction == "lower_is_better":
        verdict = "better_b" if nb < na else "better_a"
    else:
        verdict = "better_b" if nb > na else "better_a"
    return Difference(verdict=verdict, delta=delta, delta_text=delta_text, **base)


class ComparisonResult(BaseModel):
    differences: list[Difference]
    counts: dict[str, int]

    @property
    def material(self) -> list[Difference]:
        return [d for d in self.differences if d.material]


def compare(a: Policy, b: Policy) -> ComparisonResult:
    """a = current/previous, b = renewal/offer."""
    diffs = [compare_dimension(a, b, d) for d in DIMENSIONS]
    counts = {
        "better_b": sum(d.verdict == "better_b" for d in diffs),
        "better_a": sum(d.verdict == "better_a" for d in diffs),
        "same": sum(d.verdict == "same" for d in diffs),
        "needs_checking": sum(
            d.verdict in ("missing_a", "missing_b", "missing_both", "uncertain") for d in diffs
        ),
        "not_rankable": sum(d.verdict == "different_not_rankable" for d in diffs),
    }
    return ComparisonResult(differences=diffs, counts=counts)
