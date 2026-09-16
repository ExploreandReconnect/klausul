"""Profile weighting.

The user's circumstances change how much a difference matters. They never change
what the difference IS. This file therefore reads the comparison output and emits
a relevance grade — it has no ability to alter a Field or a verdict, and that
restriction is the point.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from .compare import Difference

Relevance = Literal["HIGH", "MEDIUM", "LOW"]


class Profile(BaseModel):
    annual_km: int | None = None                       # ~25000
    drives_abroad: bool | None = None
    vehicle_dependency: Literal["low", "high"] | None = None
    parking: Literal["private", "street"] | None = None
    money_preference: Literal["premium", "exposure", "balanced"] | None = None
    vehicle_value_eur: int | None = None
    additional_drivers: bool | None = None
    young_driver: bool | None = None


# Which profile answer raises which dimension, and the one-line reason shown to the
# user. Keeping the reason next to the rule means the UI can always say why a row
# is where it is.
RULES: dict[str, list[tuple[str, str]]] = {
    "cov_foreign":       [("drives_abroad", "you drive outside your home country regularly")],
    "territories":       [("drives_abroad", "you drive outside your home country regularly")],
    "cov_roadside":      [("drives_abroad", "you drive outside your home country regularly"),
                          ("vehicle_dependency_high", "you depend heavily on the car")],
    "replacement_days":  [("vehicle_dependency_high", "you depend heavily on the car")],
    "excess_theft":      [("parking_street", "you park on the street rather than off it")],
    "excess_collision":  [("high_mileage", "you drive well above average annual distance")],
    "excess_glass":      [("high_mileage", "you drive well above average annual distance")],
    "excess_young":      [("young_driver", "a young driver is on the policy")],
    "premium":           [("prefers_premium", "you told us you prioritise a lower premium")],
}

HIGH_MILEAGE_KM = 20_000


def _flags(p: Profile) -> set[str]:
    f: set[str] = set()
    if p.drives_abroad:
        f.add("drives_abroad")
    if p.vehicle_dependency == "high":
        f.add("vehicle_dependency_high")
    if p.parking == "street":
        f.add("parking_street")
    if p.annual_km and p.annual_km >= HIGH_MILEAGE_KM:
        f.add("high_mileage")
    if p.young_driver:
        f.add("young_driver")
    if p.money_preference == "premium":
        f.add("prefers_premium")
    if p.money_preference == "exposure":
        f.add("prefers_exposure")
    return f


class Weighted(BaseModel):
    difference: Difference
    relevance: Relevance
    reasons: list[str] = []


def weigh(diffs: list[Difference], profile: Profile) -> list[Weighted]:
    flags = _flags(profile)
    out: list[Weighted] = []

    for d in diffs:
        if d.verdict == "same":
            continue

        reasons = [why for flag, why in RULES.get(d.key, []) if flag in flags]

        # An unresolved item the profile makes relevant is the highest grade there is:
        # it is both important and unknown.
        unresolved = d.verdict in ("missing_a", "missing_b", "missing_both", "uncertain")

        if reasons and unresolved:
            rel: Relevance = "HIGH"
        elif reasons:
            rel = "HIGH"
        elif unresolved:
            rel = "MEDIUM"
        elif d.delta is not None and abs(d.delta) >= 200:
            rel = "MEDIUM"
        else:
            rel = "LOW"

        # Exposure-averse users care more about excesses; premium-focused users less.
        if "prefers_exposure" in flags and d.key.startswith("excess_") and rel == "LOW":
            rel = "MEDIUM"

        out.append(Weighted(difference=d, relevance=rel, reasons=reasons))

    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    return sorted(out, key=lambda w: (order[w.relevance], -abs(w.difference.delta or 0)))
