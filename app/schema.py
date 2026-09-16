"""Canonical insurance model + provenance envelope.

Every extracted value is wrapped in a Field. A bare number is never allowed into
the comparison engine: if we cannot say where a value came from, we do not have it.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field as F


class Status(str, Enum):
    EXPLICIT = "explicit"          # stated in the document
    INFERRED = "inferred"          # derived from stated text, flagged as derived
    NOT_FOUND = "not_found"        # absent — NOT the same as "not covered"
    NOT_APPLICABLE = "not_applicable"
    AMBIGUOUS = "ambiguous"        # stated but conditional or unquantified
    CONFLICTING = "conflicting"    # two parts of the document disagree


class Field(BaseModel):
    """A value plus the evidence for it. The whole product rests on this class."""
    value: Any = None
    unit: str | None = None            # "EUR", "days", "km"
    status: Status = Status.NOT_FOUND
    confidence: float = F(0.0, ge=0.0, le=1.0)
    source_document: str | None = None
    source_page: int | None = None
    source_text: str | None = None     # verbatim, original language, never translated
    note: str | None = None

    @property
    def usable(self) -> bool:
        return self.status in (Status.EXPLICIT, Status.INFERRED) and self.value is not None


class DocumentMeta(BaseModel):
    country: Field = Field()
    language: Field = Field()
    insurer: Field = Field()
    product_name: Field = Field()
    document_type: Field = Field()     # ipid | policy_terms | offer | renewal_notice
    effective_from: Field = Field()
    effective_to: Field = Field()


class Price(BaseModel):
    annual_premium: Field = Field()
    payment_frequency: Field = Field()
    fees: Field = Field()
    taxes_if_identifiable: Field = Field()


COVERAGES = (
    "third_party_liability", "collision", "comprehensive", "theft", "fire",
    "windscreen_glass", "vandalism", "natural_events", "personal_accident",
    "legal_assistance", "roadside_assistance", "replacement_vehicle", "foreign_travel",
)

EXCESSES = ("general", "collision", "theft", "glass", "young_driver")


class Policy(BaseModel):
    document: DocumentMeta = DocumentMeta()
    price: Price = Price()
    coverage: dict[str, Field] = F(default_factory=dict)
    coverage_limits: dict[str, Field] = F(default_factory=dict)
    excesses: dict[str, Field] = F(default_factory=dict)
    exclusions: list[Field] = F(default_factory=list)
    territories: Field = Field()
    foreign_use_limitations: Field = Field()
    obligations: list[Field] = F(default_factory=list)
    claims_conditions: list[Field] = F(default_factory=list)
    duration: Field = Field()
    cancellation: Field = Field()
    no_claims: Field = Field()
    uncertainties: list[str] = F(default_factory=list)

    def get(self, path: str) -> Field:
        """Dotted lookup: 'excesses.theft', 'price.annual_premium', 'coverage.roadside_assistance'."""
        head, _, tail = path.partition(".")
        node = getattr(self, head, None)
        if node is None:
            return Field()
        if not tail:
            return node if isinstance(node, Field) else Field()
        if isinstance(node, dict):
            return node.get(tail, Field())
        return getattr(node, tail, Field())


Direction = Literal["lower_is_better", "higher_is_better", "presence_is_better", "not_rankable"]


class Dimension(BaseModel):
    """One comparable thing, and how (or whether) it can be ranked mechanically."""
    key: str
    label: str
    path: str
    direction: Direction
    unit: str | None = None


# The comparison surface. Anything not listed here is reported as a difference
# but never scored better/worse.
DIMENSIONS: list[Dimension] = [
    Dimension(key="premium", label="Annual premium", path="price.annual_premium",
              direction="lower_is_better", unit="EUR"),
    Dimension(key="excess_collision", label="Collision excess", path="excesses.collision",
              direction="lower_is_better", unit="EUR"),
    Dimension(key="excess_theft", label="Theft excess", path="excesses.theft",
              direction="lower_is_better", unit="EUR"),
    Dimension(key="excess_glass", label="Windscreen & glass excess", path="excesses.glass",
              direction="lower_is_better", unit="EUR"),
    Dimension(key="excess_general", label="General excess", path="excesses.general",
              direction="lower_is_better", unit="EUR"),
    Dimension(key="excess_young", label="Young-driver excess", path="excesses.young_driver",
              direction="lower_is_better", unit="EUR"),
    Dimension(key="limit_liability_property", label="Third-party liability, property",
              path="coverage_limits.third_party_liability_property",
              direction="higher_is_better", unit="EUR"),
    Dimension(key="limit_legal", label="Legal assistance limit",
              path="coverage_limits.legal_assistance", direction="higher_is_better", unit="EUR"),
    Dimension(key="replacement_days", label="Replacement vehicle",
              path="coverage_limits.replacement_vehicle_days",
              direction="higher_is_better", unit="days"),
    Dimension(key="cov_roadside", label="Roadside assistance",
              path="coverage.roadside_assistance", direction="presence_is_better"),
    Dimension(key="cov_foreign", label="Roadside assistance, rest of Europe",
              path="coverage.foreign_travel", direction="presence_is_better"),
    Dimension(key="cov_theft", label="Theft cover", path="coverage.theft",
              direction="presence_is_better"),
    Dimension(key="cov_glass", label="Glass cover", path="coverage.windscreen_glass",
              direction="presence_is_better"),
    Dimension(key="cov_legal", label="Legal assistance", path="coverage.legal_assistance",
              direction="presence_is_better"),
    Dimension(key="territories", label="Territory covered", path="territories",
              direction="not_rankable"),
    Dimension(key="no_claims", label="No-claims record", path="no_claims",
              direction="not_rankable"),
]


# ── findings from the corpus, folded back into the comparison surface ────────
# Aviva Ireland's motor IPID carries a conditional second excess (EUR 2,500 where
# penalty points were not declared) and a time-limited territorial extension
# ("identical cover in the EU for up to 31 days"). Neither fits a single scalar,
# and flattening them would be exactly the dishonesty this schema exists to stop.

class ConditionalAmount(BaseModel):
    """An amount that only applies when something is true."""
    amount: Field = Field()
    condition: Field = Field()      # the clause, verbatim, in its own language


def extend_dimensions() -> None:
    """Additive so existing comparisons keep their keys and ordering."""
    have = {d.key for d in DIMENSIONS}
    for dim in (
        Dimension(key="foreign_days", label="Days of cover outside the home country",
                  path="coverage_limits.foreign_use_days",
                  direction="higher_is_better", unit="days"),
        Dimension(key="excess_conditional", label="Conditional extra excess",
                  path="excesses.conditional_max", direction="lower_is_better", unit="EUR"),
    ):
        if dim.key not in have:
            DIMENSIONS.append(dim)


extend_dimensions()
