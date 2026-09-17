"""An absence is checked against the document, never taken on trust.

WHY THIS EXISTS
---------------
`missing_a`, `missing_b` and `missing_both` are the only verdicts in this system that
assert a NEGATIVE. Every other verdict compares two things the model found and can be
audited by reading the two quotes. A negative has no quote by construction, so there is
nothing to audit — and the model's recall is not 1.0.

It was measured. Two real pairs, 34 dimensions, audited against the PDFs' own text:

  DK Tryg 2022 vs 2024   `territories`          reported "stated 2024, absent 2022"
                         The clause is IDENTICAL in both, under "Hvor er jeg dækket?".
  IE Aviva vs AIG        `foreign_days`         reported "neither document"
                         Aviva: "Identical cover in the EU for up to 31 days".
  IE Aviva vs AIG        `excess_conditional`   reported "neither document"
                         Aviva: "An additional policy excess of EUR 2,500 applies...".
  IE Aviva vs AIG        `territories`          reported "neither document"
                         Both carry the heading "Where am I covered?".

Four of thirty-four. The pipeline could not tell *the document is silent* from *we
failed to find it*, and presented the second as the first.

`EmptyExtraction` already enforces exactly this distinction for a WHOLE DOCUMENT: a
failure to read is not a finding about the document. This module enforces it per field.

WHAT IT DOES, AND WHAT IT REFUSES TO DO
---------------------------------------
It only ever DEMOTES. A `not_found` whose subject is demonstrably discussed in the text
becomes `ambiguous` — "the document raises this and does not settle it" — and carries the
line it was found on as evidence. It never promotes a `not_found` into a value, never
picks between candidate values, and never writes a number. Those would all be confident
answers produced by the component whose purpose is to prevent confident wrong answers.

It also makes the honest answer the more useful one. The Tryg IPID names "Vejhjælp" and
"Nulselvrisiko" in a list of optional add-ons without saying whether you have them or what
they cost. "Neither document discusses roadside assistance" is false. "Your document names
roadside assistance as an optional extra and does not say whether it is included" is true,
and it is a better question to put to an insurer.

No model call, by the same argument as compare.py.
"""
from __future__ import annotations

import re
import unicodedata

from .schema import DIMENSIONS, Field, Policy, Status
from .vocab import FIELDS, SECTIONS

# Below this, a "term" matches inside unrelated words often enough to be noise.
# "vol" (fr, theft) is inside "volume"; "brand" is a whole word in Danish but a
# substring in "branded". The boundary regex handles the second case; the length
# floor handles terms too generic to carry meaning on their own.
MIN_TERM = 4

# A field term found in a line shorter than this is a column header or a layout fragment,
# not the document discussing the subject. Section headings are exempt: they are short by
# nature, and the three that qualify are matched in full.
MIN_LINE = 25

# A section heading is only evidence where the SECTION'S CONTENT IS THE DIMENSION.
#
# This list was longer and had to be cut. Commission Implementing Regulation (EU)
# 2017/1469 makes these headings mandatory, so a heading proves the document is an IPID
# and nothing else. "Hvornår og hvordan betaler jeg?" appears in every Danish IPID ever
# written and says nothing about whether the premium amount is stated — mapping it to
# price.annual_premium demoted a true absence on both documents of both pairs.
#
# Three survive, because for these the section does not merely relate to the dimension,
# it IS the dimension: a "Where am I covered?" section answers the territorial scope, a
# "When does the cover start and end?" section answers duration, a "How do I cancel?"
# section answers cancellation. This is what catches the Tryg `territories` case, where
# the Danish field vocabulary ("dækningsområde", "geografisk område") appears nowhere and
# the heading "Hvor er jeg dækket?" appears in both documents.
SECTION_FOR: dict[str, str] = {
    "territories": "where",
    "duration": "duration",
    "cancellation": "cancel",
}


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.casefold())
    return "".join(c for c in s if not unicodedata.combining(c))


def _pattern(term: str) -> re.Pattern[str] | None:
    """Word-boundary match on the folded form.

    Substring matching is what makes a vocabulary layer dangerous: "excess" is inside
    "excessive", "vol" is inside "volume", "brand" is inside "branded". The terms are
    multi-word often enough that \\b at each end is the right shape, and \\w* between
    words absorbs inflection ("selvrisikoen").

    Punctuation is stripped rather than escaped. Keeping it cost us the whole Danish
    territory case: the heading term is "Hvor er jeg dækket?", and a trailing escaped
    "?" put the closing \\b between two non-word characters, where no boundary exists.
    The pattern could never match the heading it was written for.
    """
    parts = [re.escape(p) for p in re.findall(r"\w+", _fold(term))]
    if not parts:
        return None
    # A bounded suffix, not an open one. `\w*` absorbs inflection ("selvrisikoen" from
    # "selvrisiko") but it also absorbs meaning: it matched "excess" inside "excessively",
    # which is the substring problem the word boundaries were added to remove. Three
    # characters covers the Germanic and Romance endings this vocabulary actually meets.
    return re.compile(r"\b" + r"\w{0,3}\s+".join(parts) + r"\w{0,3}\b")


# NOT borrowed. The first version let a limit borrow its cover's vocabulary, on the
# reasoning that "replacement vehicle for up to 14 days" states both in one sentence.
# Measured, that was wrong in the direction that matters: "Legal expenses cover" proves
# legal assistance is discussed and says nothing about whether a LIMIT is stated, so the
# check demoted true absences of a limit on the strength of the cover being mentioned.
#
# A cover being present is evidence about the cover. It is not evidence about its
# amount — and the amount is the thing this product exists to find. So the four
# `coverage_limits.*` dimensions and `excesses.conditional_max` have no vocabulary of
# their own, cannot be verified, and their absences are therefore left standing. That is
# the conservative direction: an unverifiable absence stays an absence.
BORROWS: dict[str, str] = {}


def _compile(terms) -> list[tuple[re.Pattern[str], str]]:
    out = []
    for t in terms:
        if len(t) < MIN_TERM:
            continue
        p = _pattern(t)
        if p is not None:
            out.append((p, t))
    return out


_TERMS: dict[str, list[tuple[re.Pattern[str], str]]] = {
    key: _compile([t for terms in langs.values() for t in terms])
    for key, langs in FIELDS.items()
}
for _to, _from in BORROWS.items():
    _TERMS[_to] = _TERMS.get(_from, [])

_HEADINGS: dict[str, list[tuple[re.Pattern[str], str]]] = {
    s.key: _compile([t for terms in s.terms.values() for t in terms]) for s in SECTIONS
}


class Mention:
    """Where the document discusses something, and which term proved it."""

    __slots__ = ("line", "page", "term")

    def __init__(self, line: str, page: int | None, term: str):
        self.line, self.page, self.term = line, page, term


def _numbered_lines(text: str):
    """Walk the extracted text, carrying the page marker read_pdf wrote into it."""
    page: int | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = re.fullmatch(r"=== PAGE (\d+) ===", line)
        if m:
            page = int(m.group(1))
            continue
        yield line, page


def find_mention(text: str | None, path: str) -> Mention | None:
    """The line where `text` discusses `path`, or None.

    `path` is a canonical dotted key — the same spelling used by Policy.get and by
    vocab.FIELDS, so the two stay in step without a translation table.
    """
    if not text:
        return None
    field_pats = _TERMS.get(path, ())
    head_pats = _HEADINGS.get(SECTION_FOR[path], ()) if path in SECTION_FOR else ()
    if not field_pats and not head_pats:
        return None                       # nothing to check with — leave the absence alone

    for line, page in _numbered_lines(text):
        hay = _fold(line)
        # A field term has to land in a line of prose. Matching the word inside a bare
        # column header or a stray fragment is not the document discussing the subject,
        # and two-page IPIDs laid out in columns produce plenty of those fragments.
        if len(line) >= MIN_LINE:
            for pat, term in field_pats:
                if pat.search(hay):
                    return Mention(line, page, term)
        for pat, term in head_pats:
            if pat.search(hay):
                return Mention(line, page, term)
    return None


def _sentence_case(label: str) -> str:
    """Lower only the first letter. `label.lower()` turned "Roadside assistance, rest of
    Europe" into "... rest of europe" on the page — a proper noun, flattened."""
    return label[:1].lower() + label[1:] if label else label


def _demote(f: Field, m: Mention, label: str) -> None:
    doc = f.source_document
    f.status = Status.AMBIGUOUS
    f.confidence = min(f.confidence, 0.35)
    f.source_text = m.line
    f.source_page = m.page
    f.source_document = doc
    f.note = (f"this document does discuss {_sentence_case(label)} — the line below "
              f"mentions «{m.term}» — but no value for it was established, so "
              f"it is unsettled rather than absent")


def verify_absences(*policies: Policy) -> list[dict]:
    """Check every `not_found` against its own document's text. Mutates in place.

    Returns one record per absence that did not survive the check, so the reader can be
    told what happened rather than having an answer change underneath them.
    """
    out: list[dict] = []
    for dim in DIMENSIONS:
        for p in policies:
            f = p.get(dim.path)
            if f.status is not Status.NOT_FOUND:
                continue
            m = find_mention(p.source_text, dim.path)
            if m is None:
                continue
            _demote(f, m, dim.label)
            out.append({
                "field": dim.path,
                "label": dim.label,
                "document": f.source_document,
                "term": m.term,
                "page": m.page,
                "line": m.line,
            })
    return out


def absence_notes(records: list[dict]) -> list[str]:
    """Plain sentences for the uncertainties list the reader actually sees.

    Both documents usually recover the same field, so the note has to say WHICH one.
    Written as "this document" it produced the same sentence twice with nothing to tell
    them apart, which reads as a duplicate rather than as two findings.
    """
    return [
        f"{r['label']} is not absent from {r['document'] or 'this document'} — it is "
        f"discussed on page {r['page']} («{r['term']}») without a value being "
        f"stated: »{(r['line'] or '')[:110]}«"
        for r in records
    ]
