"""A failure to READ must never be presented as a finding about the DOCUMENT.

This is the twin of the PRD's `not_found` rule. It exists because we shipped the
opposite: an empty extraction became eighteen confident "could not be established"
rows plus a generated question list, none of which said the real thing — that the
model had not read the documents.
"""
import pytest

from app import extract as EX
from app.schema import Status


def _policy(raw):
    return EX.to_policy(raw, "doc.pdf")


GROUNDED = {"excesses": {"theft": {"value": 300, "status": "explicit",
                                   "source_text": "Selvrisiko ved tyveri: 300 EUR",
                                   "source_page": 1}}}


def test_all_not_found_is_no_evidence():
    assert EX.evidence_count(_policy({})) == 0
    assert EX.evidence_count(_policy({"excesses": {"theft": {"status": "not_found"}}})) == 0


def test_one_grounded_field_is_evidence():
    assert EX.evidence_count(_policy(GROUNDED)) >= 1


def test_empty_extraction_raises_rather_than_returning_a_blank_policy(monkeypatch):
    calls = []

    def always_empty(system, user, *, model=None, stats=None, **kw):
        calls.append(1)
        if stats is not None:
            stats.update(finish_reason="length", completion_tokens=8000, max_tokens=16000)
        return {}

    monkeypatch.setattr(EX, "complete_json", always_empty)
    monkeypatch.setattr(EX, "read_pdf", lambda p: "=== PAGE 1 ===\nreal text here\n" * 20)

    with pytest.raises(EX.EmptyExtraction) as err:
        EX.extract("doc.pdf", market="DK")

    assert len(calls) == 2, "an empty draw must be retried exactly once"
    assert "finish_reason" in str(err.value), "the diagnosis must travel with the error"


def test_a_bad_draw_followed_by_a_good_one_recovers(monkeypatch):
    calls = []

    def flaky(system, user, *, model=None, stats=None, **kw):
        calls.append(1)
        return {} if len(calls) == 1 else GROUNDED

    monkeypatch.setattr(EX, "complete_json", flaky)
    monkeypatch.setattr(EX, "read_pdf", lambda p: "=== PAGE 1 ===\nreal text\n" * 20)

    p = EX.extract("doc.pdf", market="DK")
    assert EX.evidence_count(p) >= 1
    assert len(calls) == 2


def test_empty_extraction_is_not_a_value_error():
    """A ValueError means "this PDF has no text layer" and returns 422. A failed read
    is a different failure with a different answer, and must not be mistaken for it."""
    e = EX.EmptyExtraction("doc.pdf", chars=900, stats={})
    assert not isinstance(e, ValueError)
