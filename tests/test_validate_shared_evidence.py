"""One quote cannot be the sole evidence for two UNRELATED claims.

NARROWED AFTER MEASUREMENT. The first version demoted every field that shared a quote.
Run over two real pairs it fired six times and was right once; the five wrong ones were
all one sentence carrying two related facts — "Fire, theft or attempted theft", or
"Identical cover in the EU for up to 31 days" (a benefit and its scope). It cost us the
Aviva 31-day limit, and it contradicted vocab.match_all, which says in its own docstring
that one clause routinely carries a benefit AND a scope.

The case this module was built for — the Tryg territory clause cited for both
`territories` and roadside assistance in the rest of Europe — is INSIDE the territory
family, so it is deliberately no longer caught here. It does not need to be. The damage
was never the shared quote; it was the unverified ABSENCE on the other document, and
app/absence.py checks that directly. See test_the_real_tryg_artefact_is_caught_elsewhere.
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


def test_a_quote_shared_inside_one_family_is_normal_drafting():
    """A territory clause is evidence for territory and for cover abroad, at once.

    This is the Tryg pair. Demoting both was the first fix and it was the wrong one:
    it threw away a correct value to defend against a defect that lives elsewhere.
    """
    p = _policy(territories=_f("Europa", TRYG), cov_foreign_travel=_f(True, TRYG))
    assert shared_evidence(p) == []
    assert p.territories.status is Status.EXPLICIT
    assert p.coverage["foreign_travel"].status is Status.EXPLICIT


def test_a_peril_list_is_one_sentence_about_several_covers():
    """From ie-aviva-motorcare.pdf: "Fire, theft or attempted theft - loss of or damage
    to your car". Both perils really are covered by that sentence."""
    quote = "Fire, theft or attempted theft - loss of or damage to your car"
    p = _policy(cov_fire=_f(True, quote), cov_theft=_f(True, quote))
    assert shared_evidence(p) == []
    assert p.coverage["fire"].status is Status.EXPLICIT


def test_a_quote_stretched_across_families_still_settles_nothing():
    """A theft-excess figure and a cancellation term are not one subject."""
    quote = "Selvrisikoen udgør 3.000 kr. ved enhver skade paa koeretoejet."
    p = _policy(cancellation=_f("x", quote))
    p.excesses["theft"] = _f(3000, quote)
    conflicts = shared_evidence(p)
    assert len(conflicts) == 1
    assert sorted(conflicts[0]["fields"]) == ["cancellation", "excesses.theft"]
    assert p.cancellation.status is Status.AMBIGUOUS
    assert p.excesses["theft"].status is Status.AMBIGUOUS


def test_neither_side_is_promoted_over_the_other():
    """Arbitration was tried and rejected: vocab.match_all returns the same key for
    both of these clauses, so picking a winner picks wrong. Refusing is the fix."""
    quote = "Selvrisikoen udgoer 3.000 kr. ved enhver skade paa koeretoejet."
    p = _policy(cancellation=_f("x", quote))
    p.excesses["theft"] = _f(3000, quote)
    shared_evidence(p)
    assert p.cancellation.status is p.excesses["theft"].status
    assert p.cancellation.confidence == p.excesses["theft"].confidence


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
    quote = "Selvrisikoen udgoer 3.000 kr. ved enhver skade paa koeretoejet."
    p = _policy(cancellation=_f("x", quote))
    p.excesses["theft"] = _f(3000, quote)
    notes = conflict_notes(shared_evidence(p))
    assert len(notes) == 1
    assert "2 different fields" in notes[0]
    assert "Selvrisikoen" in notes[0]


def test_the_note_names_the_other_field():
    quote = "Selvrisikoen udgoer 3.000 kr. ved enhver skade paa koeretoejet."
    p = _policy(cancellation=_f("x", quote))
    p.excesses["theft"] = _f(3000, quote)
    shared_evidence(p)
    assert "excesses.theft" in p.cancellation.note
    assert "cancellation" in p.excesses["theft"].note


def test_the_real_tryg_artefact_is_caught_elsewhere():
    """The defect that started all of this, killed at its actual source.

    The 2024 document cites the territory clause for roadside cover abroad. The 2022
    document carries the identical clause and the model did not return it, so the
    comparison said the cover had been ADDED at renewal. The absence check reads the
    2022 text, finds the clause, and the absence never reaches compare().
    """
    from app.absence import verify_absences
    from app.compare import compare_dimension
    from app.schema import DIMENSIONS, extend_dimensions
    extend_dimensions()
    dim = next(d for d in DIMENSIONS if d.path == "coverage.foreign_travel")

    text_2022 = ("=== PAGE 2 ===\nHvor er jeg daekket?\n"
                 "Forsikringen gaelder i Europa samt i de lande uden for Europa, "
                 "der er tilsluttet Groent kort ordningen.")
    a = Policy(source_text=text_2022)
    a.coverage["foreign_travel"] = Field(status=Status.NOT_FOUND)
    b = Policy(source_text=text_2022)
    b.coverage["foreign_travel"] = _f(True, TRYG)

    assert compare_dimension(a, b, dim).verdict == "missing_a"   # before the check
    verify_absences(a, b)
    assert compare_dimension(a, b, dim).verdict == "uncertain"   # after it


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
