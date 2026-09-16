"""The explanation layer must not force a claim scenario onto a field that has nothing
to do with claims.

It shipped doing exactly that: every row was explained as "what it would mean if you had
a claim", which produced "If you have a claim, you will need to pay 90 EUR more in
premiums" for a premium that rises whether or not you ever claim.
"""
from app.explain import _direction, _frame


class _F:
    def __init__(self, v):
        self.value = v


class _D:
    def __init__(self, key, a, b, verdict, label="x", unit="EUR"):
        self.key, self.a, self.b = key, _F(a), _F(b)
        self.verdict, self.label, self.unit = verdict, label, unit


def test_a_premium_is_not_framed_as_a_claim_event():
    f = _frame("premium")
    assert "whether or not" in f
    assert "Do NOT describe it as something that happens at claim time" in f


def test_an_excess_is_framed_as_a_claim_event():
    assert "out of your own pocket on an eligible claim" in _frame("excess_theft")


def test_a_limit_is_framed_as_the_insurer_ceiling():
    assert "most the insurer will pay" in _frame("limit_legal")


def test_an_unknown_key_does_not_assume_a_claim():
    assert "Do not assume a claim scenario" in _frame("something_new")


def test_direction_states_a_rise_as_a_rise():
    d = _D("premium", 720.0, 810.0, "better_a", "Annual premium")
    text = _direction(d)
    assert "ROSE" in text and "90.0" in text
    assert "worse for the reader" in text


def test_direction_states_a_fall_as_a_fall():
    d = _D("excess_glass", 150.0, 100.0, "better_b", "Glass excess")
    assert "FELL" in _direction(d)


def test_direction_handles_a_field_with_no_number():
    d = _D("cov_roadside", None, "covered", "missing_a", "Roadside")
    assert "no single figure" in _direction(d)
