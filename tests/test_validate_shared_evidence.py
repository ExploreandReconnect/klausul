"""One quote cannot be the sole evidence for two claims.

From the real Tryg 2022/2024 pair: the territory clause was cited as evidence BOTH for
`territories` and for roadside assistance in the rest of Europe, in the 2024 document
only. The comparison engine then reported that European roadside cover had been added
at renewal. It had not. It is a territory clause.
"""
import pytest

from app.schema import Field, Policy, Status
from app.validate import _norm, conflict_notes, shared_evidence

TRYG = ("Forsikringen gælder i Europa samt i de lande uden for Europa, "
        "der er tilsluttet 'Grønt kort ordningen'")
TRYG_OTHER_APOSTROPHE = TRYG.replace("'", "''")


def _f(value, quote, status=Status.EXPLICIT):
    return Field(value=value, status=status, confidence=0.95,
                 source_document="doc.pdf", source_page=1, source_text=quote)


def _policy(**fields):
    p = Policy()
    for k, v in fields.items():
        if k.startswith("cov_"):
            p.coverage[k[4:]] = v
        else:
            setattr(p, k, v)
    return p


def test_the_real_tryg_artefact_is_caught():
    p = _policy(territories=_f("Europa", TRYG), cov_foreign_travel=_f(True, TRYG))
    conflicts = shared_evidence(p)
    assert len(conflicts) == 1
    assert sorted(conflicts[0]["fields"]) == ["coverage.foreign_travel", "territories"]
    assert p.territories.status is Status.AMBIGUOUS
    assert p.coverage["foreign_travel"].status is Status.AMBIGUOUS


def test_neither_side_is_promoted_over_the_other():
    """Arbitration was tried and rejected: vocab.match_all returns the same key for
    both of these clauses, so picking a winner picks wrong. Refusing is the fix."""
    p = _policy(territories=_f("Europa", TRYG), cov_foreign_travel=_f(True, TRYG))
    shared_evidence(p)
    assert p.territories.status is p.coverage["foreign_travel"].status
    assert p.territories.confidence == p.coverage["foreign_travel"].confidence


def test_punctuation_does_not_hide_the_reuse():
    """The same clause appears with ' and '' across the two Tryg documents."""
    assert _norm(TRYG) == _norm(TRYG_OTHER_APOSTROPHE)


def test_distinct_quotes_are_left_alone():
    p = _policy(territories=_f("Europa", TRYG),
                cov_foreign_travel=_f(True, "Vejhjælp i Europa er omfattet af dækningen."))
    assert shared_evidence(p) == []
    assert p.territories.status is Status.EXPLICIT
    assert p.coverage["foreign_travel"].status is Status.EXPLICIT


def test_short_fragments_are_not_treated_as_evidence_reuse():
    """'EUR 300' repeating across fields is not the failure this guards against."""
    p = _policy(territories=_f("x", "EUR 300"), cov_foreign_travel=_f(True, "EUR 300"))
    assert shared_evidence(p) == []


def test_a_field_with_no_quote_is_not_a_conflict():
    p = _policy(territories=Field(status=Status.NOT_FOUND),
                cov_foreign_travel=Field(status=Status.NOT_FOUND))
    assert shared_evidence(p) == []


def test_the_conflict_is_told_to_the_reader():
    p = _policy(territories=_f("Europa", TRYG), cov_foreign_travel=_f(True, TRYG))
    notes = conflict_notes(shared_evidence(p))
    assert len(notes) == 1
    assert "2 different fields" in notes[0]
    assert "Forsikringen gælder" in notes[0]


def test_the_note_names_the_other_field():
    p = _policy(territories=_f("Europa", TRYG), cov_foreign_travel=_f(True, TRYG))
    shared_evidence(p)
    assert "coverage.foreign_travel" in p.territories.note
    assert "territories" in p.coverage["foreign_travel"].note


def test_an_unsettled_value_never_produces_a_missing_finding():
    """`missing_a` claims the other document states this and yours does not. That is a
    finding, and it requires the other side to actually assert something. With the
    checks in the old order, an ambiguous value still produced it — which is how the
    Tryg pair reported European roadside cover as ADDED at renewal."""
    from app.compare import compare_dimension
    from app.schema import DIMENSIONS, extend_dimensions
    extend_dimensions()
    dim = next(d for d in DIMENSIONS if d.path == "coverage.foreign_travel")

    a, b = Policy(), Policy()
    a.coverage["foreign_travel"] = Field(status=Status.NOT_FOUND)
    b.coverage["foreign_travel"] = _f(True, TRYG, status=Status.AMBIGUOUS)
    assert compare_dimension(a, b, dim).verdict == "uncertain"

    # a genuinely asserted value on one side is still a finding
    b.coverage["foreign_travel"] = _f(True, "Vejhjælp i Europa er omfattet af dækningen.")
    assert compare_dimension(a, b, dim).verdict == "missing_a"
