"""The comparison engine must never invent a difference, and never resolve an absence."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app.compare import compare, compare_dimension
from app.schema import DIMENSIONS, Field, Policy, Status

D = {d.key: d for d in DIMENSIONS}


def excess(value, status=Status.EXPLICIT, conf=0.97):
    p = Policy()
    p.excesses = {"theft": Field(value=value, unit="EUR", status=status,
                                 confidence=conf, source_text="x", source_page=1)}
    return p


def test_absence_is_never_resolved():
    a, b = excess(300), Policy()
    d = compare_dimension(a, b, D["excess_theft"])
    assert d.verdict == "missing_b"


def test_absence_on_both_sides_favours_neither():
    d = compare_dimension(Policy(), Policy(), D["excess_theft"])
    assert d.verdict == "missing_both"


def test_lower_excess_is_better():
    d = compare_dimension(excess(500), excess(300), D["excess_theft"])
    assert d.verdict == "better_b" and d.delta == -200


def test_identical_is_not_a_difference():
    d = compare_dimension(excess(500), excess(500), D["excess_theft"])
    assert d.verdict == "same" and not d.material


def test_low_confidence_becomes_uncertain_not_a_ranking():
    d = compare_dimension(excess(500), excess(300, conf=0.4), D["excess_theft"])
    assert d.verdict == "uncertain"


def test_ambiguous_is_never_ranked():
    d = compare_dimension(excess(500), excess(0, status=Status.AMBIGUOUS), D["excess_theft"])
    assert d.verdict == "uncertain"


def test_no_invented_differences():
    r = compare(Policy(), Policy())
    assert not any(d.verdict in ("better_a", "better_b") for d in r.differences)
