"""The number convention is the only bug in this project that is silently 100x wrong."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import pytest
from app.vocab import parse_amount, match_field, match_all, match_section


@pytest.mark.parametrize("text,market,expected", [
    ("Selvrisiko: 1.250,00 kr.", "DK", 1250.0),
    ("Jahresbeitrag inkl. Versicherungsteuer: 810,00 EUR", "DE", 810.0),
    ("the standard excess is 2,500", "IE", 2500.0),
    ("1 234,56", "FR", 1234.56),
    ("EUR 1.234,56", "NL", 1234.56),
])
def test_amounts(text, market, expected):
    assert parse_amount(text, market) == expected


def test_same_digits_different_markets():
    """This is the whole argument for passing the market into extraction."""
    assert parse_amount("2,500", "IE") == 2500.0
    assert parse_amount("2,500", "DE") == 2.5


def test_unknown_market_returns_none_rather_than_guessing():
    assert parse_amount("2,500", "XX") is None


@pytest.mark.parametrize("text,key", [
    ("Selvrisiko ved tyveri og røveri: 500 EUR", "excesses.theft"),
    ("Selbstbeteiligung Vollkasko: 700 EUR", "excesses.collision"),
    ("Selvrisiko ved glasskade: 100 EUR", "excesses.glass"),
    ("Der Schadenfreiheitsrabatt wird übernommen", "no_claims"),
])
def test_specific_beats_general(text, key):
    assert match_field(text) == key


def test_one_clause_can_carry_two_meanings():
    hits = match_all("Vejhjælp i Europa er omfattet af dækningen")
    assert "coverage.roadside_assistance" in hits
    assert "coverage.foreign_travel" in hits


@pytest.mark.parametrize("heading,key", [
    ("Are there any restrictions on cover?", "restrictions"),
    ("Hvor er jeg dækket?", "where"),
    ("Gibt es Deckungsbeschränkungen?", "restrictions"),
    ("Wat is niet verzekerd?", "not_insured"),
])
def test_sections_match_semantically(heading, key):
    assert match_section(heading) == key
