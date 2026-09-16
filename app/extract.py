"""PDF -> canonical Policy, with provenance on every field.

Pages are extracted with page numbers attached so the model can cite them, and the
prompt forbids the two failure modes that would sink the product: inventing a value,
and turning an absence into a zero or a "no".
"""
from __future__ import annotations

import json
from pathlib import Path

import pdfplumber
from pydantic import ValidationError

from .nebius import MODEL_EXTRACT, complete_json
from .vocab import NUMBER_FORMATS
from .schema import COVERAGES, EXCESSES, Field, Policy, Status

SYSTEM = """You extract structured data from European motor-insurance documents.

You are given the full text of one document, page by page. Return JSON only.

Absolute rules:
1. Never invent a value. If the document does not state something, the field's status
   is "not_found" and its value is null.
2. "not_found" does not mean "not covered". Never write false, 0 or "excluded" for a
   field the document is silent about.
3. source_text must be copied VERBATIM from the document, in the document's own
   language. Do not translate it, tidy it, or paraphrase it.
4. source_page must be the page number the quote appears on.
5. If a value is stated but CONDITIONAL, status is "ambiguous" and note states the
   condition. Conditional values are common and must not be flattened:
     - "no excess on repair; on replacement clause 7.3 applies" -> ambiguous
     - "standard excess EUR 300, plus EUR 2,500 if penalty points were not declared"
       -> excesses.general = 300 explicit, and the 2,500 goes in excesses.other with
       its condition. Never merge the two into one number.
     - "courtesy car only if you use our own repair network" -> ambiguous
6. If two passages disagree, status is "conflicting" and note says how.
7. confidence is your own calibrated probability that the value is correct, 0.0-1.0.
   A clean figure in a fee table is ~0.97. A figure you pieced together is ~0.6.

FIND SECTIONS BY MEANING, NEVER BY POSITION OR COUNT. The nine IPID headings in
Commission Implementing Regulation (EU) 2017/1469 are required, but EIOPA confirms
manufacturers may build their own document, and real IPIDs deviate: documents with
eight sections, merged headings, and a different order are normal. Locate each
section by what it says, and if a section is genuinely absent, say so in
uncertainties rather than borrowing content from a neighbouring one.

Field keys are language-independent. Map the local term to the canonical key:
  selvrisiko / Selbstbeteiligung / franchise / eigen risico / excess -> excesses.*
  praemie / Beitrag / prime / premie -> price.annual_premium
  vejhjaelp / Schutzbrief / assistance / pechhulp -> coverage.roadside_assistance
  retshjaelp / Rechtsschutz / protection juridique -> coverage.legal_assistance

NUMBERS. The market is given to you. Use ITS convention, do not guess:
  DK  1.234,56 kr.   comma decimal, point thousands, DKK
  DE  1.234,56 EUR   comma decimal, point thousands, EUR
  IE  EUR 1,234.56   POINT decimal, comma thousands, EUR
  FR  1 234,56 EUR   comma decimal, space thousands, EUR
  NL  EUR 1.234,56   comma decimal, point thousands, EUR
Return a plain number and put the currency code in "unit". "810,00 EUR" in a DK or
DE document is 810.0, never 81000. Do not convert currencies.

TERRITORY may be a list plus a TIME LIMIT ("identical cover in the EU for up to 31
days"). Put the list in territories and the limit in foreign_use_limitations with
its own quote. A time-limited extension is not the same as full cover."""

SHAPE = """Return exactly this shape. Every leaf is an object
{{"value":..., "unit":..., "status":..., "confidence":..., "source_page":..., "source_text":...}}.

{{
  "document": {{"country":F,"language":F,"insurer":F,"product_name":F,"document_type":F,
                "effective_from":F,"effective_to":F}},
  "price": {{"annual_premium":F,"payment_frequency":F,"fees":F,"taxes_if_identifiable":F}},
  "coverage": {{{coverages}}},
  "coverage_limits": {{"third_party_liability_property":F,"third_party_liability_personal":F,
                       "legal_assistance":F,"replacement_vehicle_days":F}},
  "excesses": {{{excesses}}},
  "territories": F,
  "foreign_use_limitations": F,
  "no_claims": F,
  "duration": F,
  "cancellation": F,
  "exclusions": [F],
  "obligations": [F],
  "uncertainties": ["plain-language note about anything you could not resolve"]
}}

coverage.* values are true/false/null. A coverage present in the document is true;
one explicitly excluded is false with status "explicit"; one not mentioned at all is
null with status "not_found"."""


def read_pdf(path: str | Path) -> str:
    out = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                out.append(f"\n=== PAGE {i} ===\n{text}")
    if not out:
        raise ValueError(f"No extractable text in {path}. Scanned PDF? Route it to the omni model.")
    return "\n".join(out)


def _coerce(raw: dict, doc_name: str) -> Field:
    if not isinstance(raw, dict):
        return Field(status=Status.NOT_FOUND)
    try:
        f = Field(**{k: v for k, v in raw.items() if k in Field.model_fields})
    except ValidationError:
        return Field(status=Status.NOT_FOUND, note="rejected by schema validation")
    f.source_document = doc_name
    # A value with no quote behind it is not evidence. Demote it.
    if f.status in (Status.EXPLICIT, Status.INFERRED) and not f.source_text:
        f.status = Status.AMBIGUOUS
        f.confidence = min(f.confidence, 0.5)
        f.note = "no source quote returned"
    return f


def to_policy(raw: dict, doc_name: str) -> Policy:
    p = Policy()
    for section in ("document", "price"):
        for name in getattr(p, section).model_fields:
            setattr(getattr(p, section), name,
                    _coerce((raw.get(section) or {}).get(name, {}), doc_name))
    p.coverage = {k: _coerce((raw.get("coverage") or {}).get(k, {}), doc_name) for k in COVERAGES}
    p.coverage_limits = {k: _coerce(v, doc_name)
                         for k, v in (raw.get("coverage_limits") or {}).items()}
    p.excesses = {k: _coerce((raw.get("excesses") or {}).get(k, {}), doc_name) for k in EXCESSES}
    for name in ("territories", "foreign_use_limitations", "no_claims", "duration", "cancellation"):
        setattr(p, name, _coerce(raw.get(name, {}), doc_name))
    p.exclusions = [_coerce(x, doc_name) for x in (raw.get("exclusions") or [])]
    p.obligations = [_coerce(x, doc_name) for x in (raw.get("obligations") or [])]
    p.uncertainties = [str(u) for u in (raw.get("uncertainties") or [])]
    return p


def extract(path: str | Path, *, model: str = MODEL_EXTRACT, market: str | None = None) -> Policy:
    """`market` is an ISO-2 code (DK/DE/IE/FR/NL). It selects the number convention,
    which is a 100x error if guessed wrong — see app.vocab.NUMBER_FORMATS."""
    path = Path(path)
    text = read_pdf(path)
    shape = SHAPE.format(
        coverages=",".join(f'"{c}":F' for c in COVERAGES),
        excesses=",".join(f'"{e}":F' for e in EXCESSES) + ',"other":[F]',
    )
    hint = ""
    if market:
        fmt = NUMBER_FORMATS.get(market)
        hint = (f"\nMARKET: {market}. Numbers in this document follow "
                f"{fmt.example} — decimal '{fmt.decimal}', thousands "
                f"'{fmt.thousands or 'space'}', currency {fmt.currency}.\n") if fmt else \
               f"\nMARKET: {market} (convention unknown — state low confidence on any amount).\n"
    raw = complete_json(SYSTEM, f"{shape}{hint}\nDOCUMENT: {path.name}\n{text}", model=model)
    return to_policy(raw, path.name)


def load_fixture(path: str | Path) -> Policy:
    """Offline path: a cached extraction run. Used so a demo never depends on wifi."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return to_policy(raw, raw.get("_source_document", Path(path).stem))
