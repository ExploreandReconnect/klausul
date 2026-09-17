"""An absence must survive contact with the document, or it is not reported.

Every fixture here is text copied from a real published IPID in corpus/pdf/.
"""
from __future__ import annotations

from app.absence import MIN_LINE, absence_notes, find_mention, verify_absences
from app.schema import Field, Policy, Status

# corpus/pdf/DK/dk-tryg-2022.pdf and dk-tryg-current.pdf — the clause is identical in
# both, which is precisely why reporting it as "stated in 2024, absent in 2022" was wrong.
TRYG = """
=== PAGE 1 ===
Bilforsikringen indeholder den lovpligtig ansvarsforsikring, som kan kombineres med en
kaskoforsikring inkl. redningshjælp i udlandet og retshjælp.
tilvalgsdækninger - fx Førerdækning, Vejhjælp, Nulselvrisiko og Glas m.m.
=== PAGE 2 ===
Hvor er jeg dækket?
Forsikringen gælder i Europa samt i de lande uden for Europa, der er tilsluttet
”Grønt kort ordningen”.
"""

# corpus/pdf/IE/ie-aig.pdf — AIG names the excess and sends you to another document for
# the number. That is not silence, and the difference matters to a reader deciding which
# document to demand.
AIG = """
=== PAGE 1 ===
! An excess will apply, please see your policy schedule for details.
=== PAGE 2 ===
Where am I covered?
"""


def _policy(text: str, **fields: Field) -> Policy:
    p = Policy(source_text=text)
    for path, f in fields.items():
        head, _, tail = path.partition(".")
        if tail:
            getattr(p, head)[tail] = f
        else:
            setattr(p, head, f)
    return p


# ── find_mention ─────────────────────────────────────────────────────────────

def test_a_mandatory_section_heading_settles_the_dimension_it_names():
    """'Hvor er jeg dækket?' is the heading, and its section IS the territory answer.

    The Danish field vocabulary for territories ('dækningsområde', 'geografisk område')
    appears nowhere in this document, so the heading is the only route to the fact — and
    without it the pipeline reported the clause as absent from one of two identical
    documents.
    """
    m = find_mention(TRYG, "territories")
    assert m is not None
    assert m.page == 2


def test_a_mandatory_heading_is_not_evidence_for_a_dimension_it_merely_relates_to():
    """Every IPID carries 'When and how do I pay?' by regulation.

    Reading that as evidence that the premium is stated demoted a true absence on all
    four documents of both recorded pairs. A heading fixed by Commission Implementing
    Regulation (EU) 2017/1469 proves the document is an IPID and nothing else.
    """
    assert find_mention(TRYG, "price.annual_premium") is None


def test_a_named_optional_extra_counts_as_discussed():
    m = find_mention(TRYG, "coverage.roadside_assistance")
    assert m is not None and "Vejhjælp" in m.line


def test_a_cover_that_is_never_mentioned_stays_absent():
    assert find_mention(TRYG, "coverage.vandalism") is None
    assert find_mention(TRYG, "no_claims") is None


def test_a_dimension_with_no_vocabulary_is_left_alone():
    """A limit borrows nothing from its cover.

    'Legal expenses cover' proves legal assistance is discussed. It says nothing about
    whether a LIMIT is stated, and the limit is the thing the reader came for. An
    absence we cannot check is left standing — the conservative direction.
    """
    assert find_mention(TRYG, "coverage_limits.legal_assistance") is None
    assert find_mention(TRYG, "coverage_limits.replacement_vehicle_days") is None


def test_a_deferral_is_not_a_silence():
    m = find_mention(AIG, "excesses.general")
    assert m is not None and "policy schedule" in m.line


def test_a_term_inside_a_longer_word_does_not_match():
    assert find_mention("=== PAGE 1 ===\nThe premium was excessively branded nonsense here.",
                        "excesses.general") is None


def test_a_field_term_in_a_layout_fragment_does_not_count():
    """Two-page IPIDs are laid out in columns and the text extractor emits stubs."""
    short = "=== PAGE 1 ===\nVejhjælp"
    assert len("Vejhjælp") < MIN_LINE
    assert find_mention(short, "coverage.roadside_assistance") is None


def test_no_text_means_no_verdict():
    assert find_mention(None, "territories") is None
    assert find_mention("", "territories") is None


# ── verify_absences ──────────────────────────────────────────────────────────

def test_an_absence_the_document_contradicts_becomes_unsettled_not_absent():
    a = _policy(TRYG, territories=Field(status=Status.NOT_FOUND))
    b = _policy(TRYG, territories=Field(value="Europa", status=Status.EXPLICIT,
                                        confidence=.95, source_text="Forsikringen gælder"))
    records = verify_absences(a, b)

    assert a.territories.status is Status.AMBIGUOUS
    assert a.territories.value is None          # demoted, never filled in
    assert a.territories.source_text            # and it now carries the line it was found on
    assert b.territories.status is Status.EXPLICIT   # the side that asserted is untouched
    assert "territories" in [r["field"] for r in records]


def test_the_check_never_promotes_an_absence_into_a_value():
    a = _policy(TRYG, territories=Field(status=Status.NOT_FOUND))
    verify_absences(a)
    assert a.territories.value is None
    assert a.territories.status is not Status.EXPLICIT
    assert a.territories.confidence <= 0.35


def test_a_stated_value_is_never_touched():
    a = _policy(TRYG, territories=Field(value="Europa", status=Status.EXPLICIT, confidence=.95))
    records = verify_absences(a)
    assert "territories" not in [r["field"] for r in records]
    assert a.territories.status is Status.EXPLICIT
    assert a.territories.confidence == .95


def test_a_genuine_silence_survives_the_check():
    """The whole point is that this still reports as an absence."""
    a = _policy(TRYG)
    a.coverage["vandalism"] = Field(status=Status.NOT_FOUND)
    records = verify_absences(a)
    assert "coverage.vandalism" not in [r["field"] for r in records]
    assert a.coverage["vandalism"].status is Status.NOT_FOUND


def test_a_policy_with_no_text_is_not_second_guessed():
    a = _policy(None, territories=Field(status=Status.NOT_FOUND))
    assert verify_absences(a) == []
    assert a.territories.status is Status.NOT_FOUND


def test_the_reader_is_told_what_changed():
    a = _policy(TRYG, territories=Field(status=Status.NOT_FOUND))
    notes = absence_notes([r for r in verify_absences(a) if r["field"] == "territories"])
    assert len(notes) == 1
    assert "not absent" in notes[0]
    assert "Hvor er jeg dækket" in notes[0]


def test_source_text_never_reaches_the_wire():
    """It is working material, not part of the answer, and it is the whole PDF."""
    assert "source_text" not in Policy(source_text=TRYG).model_dump()
