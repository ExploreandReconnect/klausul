"""The vocabulary layer — the actual asset.

Commission Implementing Regulation (EU) 2017/1469 harmonises the IPID's *container*:
nine sections, an order, a page limit, an icon set. It harmonises none of the contents.
So this file is the other half: local term -> language-independent canonical key.

Two things were established empirically and both matter here.

1. SECTION ORDER IS NOT RELIABLE IN PRACTICE. EIOPA states that manufacturers
   "are not obliged to use these specific files and may choose instead to develop
   their own IPIDs that meet the requirements of the IPID Implementing Regulation."
   The Aviva Ireland motor IPID carries EIGHT sections, not nine, and puts
   restrictions after territory and cancellation before start/end. Section matching
   must therefore be SEMANTIC, never positional.

2. NUMBER FORMAT VARIES BY MARKET, and getting it wrong is a 100x error.
   "810,00 EUR" is 810.0, not 81000. See NUMBER_FORMATS.

`verified` marks a term seen in a real published document, not one we believe in.
Everything starts False. Raising these to True is what the corpus is for — and a
term that stays False after the corpus run is a gap, not a detail.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field


# ── number formats ───────────────────────────────────────────────────────────
@dataclass(frozen=True)
class NumberFormat:
    market: str
    decimal: str
    thousands: str
    currency: str
    example: str


NUMBER_FORMATS = {
    "DK": NumberFormat("DK", ",", ".", "DKK", "1.234,56 kr."),
    "DE": NumberFormat("DE", ",", ".", "EUR", "1.234,56 EUR"),
    "IE": NumberFormat("IE", ".", ",", "EUR", "€1,234.56"),
    "FR": NumberFormat("FR", ",", " ", "EUR", "1 234,56 €"),
    "NL": NumberFormat("NL", ",", ".", "EUR", "€ 1.234,56"),
}

_AMOUNT = re.compile(r"(-?[\d][\d\s., ]*)")


def parse_amount(text: str, market: str) -> float | None:
    """Parse a money amount using the market's convention, not a guess.

    >>> parse_amount("Selvrisiko: 1.250,00 kr.", "DK")
    1250.0
    >>> parse_amount("the standard excess is €2,500", "IE")
    2500.0
    """
    fmt = NUMBER_FORMATS.get(market)
    if fmt is None:
        return None
    m = _AMOUNT.search(text.replace(" ", " "))
    if not m:
        return None
    raw = m.group(1).strip()
    if fmt.thousands:
        raw = raw.replace(fmt.thousands, "")
    raw = raw.replace(" ", "")
    if fmt.decimal != ".":
        raw = raw.replace(fmt.decimal, ".")
    try:
        return float(raw)
    except ValueError:
        return None


# ── section headings ─────────────────────────────────────────────────────────
@dataclass
class Section:
    key: str
    en: str
    terms: dict[str, list[str]] = field(default_factory=dict)
    verified: set[str] = field(default_factory=set)


SECTIONS: list[Section] = [
    Section("type", "What is this type of insurance?", {
        "da": ["Hvilken form for forsikring er der tale om?"],
        "de": ["Um welche Art von Versicherung handelt es sich?"],
        "en": ["What is this type of insurance?"],
        "fr": ["De quel type d'assurance s'agit-il"],
        "nl": ["Welk soort verzekering is dit?"]}),
    Section("insured", "What is insured?", {
        "da": ["Hvad dækker den?", "Hvad er dækket?"],
        "de": ["Was ist versichert?"],
        "en": ["What is insured?"],
        "fr": ["Qu'est-ce qui est assuré"],
        "nl": ["Wat is verzekerd?"]}, verified={"en"}),
    Section("not_insured", "What is not insured?", {
        "da": ["Hvad dækker den ikke?", "Hvad er ikke dækket?"],
        "de": ["Was ist nicht versichert?"],
        "en": ["What is not insured?"],
        "fr": ["Qu'est-ce qui n'est pas assuré"],
        "nl": ["Wat is niet verzekerd?"]}, verified={"en"}),
    Section("restrictions", "Are there any restrictions on cover?", {
        "da": ["Er der nogen begrænsninger i dækningen?"],
        "de": ["Gibt es Deckungsbeschränkungen?"],
        "en": ["Are there any restrictions on cover?"],
        "fr": ["Y a-t-il des exclusions à la couverture"],
        "nl": ["Zijn er dekkingsbeperkingen?"]}, verified={"en"}),
    Section("where", "Where am I covered?", {
        "da": ["Hvor er jeg dækket?"],
        "de": ["Wo bin ich versichert?"],
        "en": ["Where am I covered?"],
        "fr": ["Où suis-je couvert"],
        "nl": ["Waar ben ik gedekt?"]}, verified={"en"}),
    Section("obligations", "What are my obligations?", {
        "da": ["Hvilke forpligtelser har jeg?"],
        "de": ["Welche Verpflichtungen habe ich?"],
        "en": ["What are my obligations?"],
        "fr": ["Quelles sont mes obligations"],
        "nl": ["Wat zijn mijn verplichtingen?"]}, verified={"en"}),
    Section("payment", "When and how do I pay?", {
        "da": ["Hvornår og hvordan betaler jeg?"],
        "de": ["Wann und wie zahle ich?"],
        "en": ["When and how do I pay?"],
        "fr": ["Quand et comment effectuer les paiements"],
        "nl": ["Wanneer en hoe betaal ik?"]}, verified={"en"}),
    Section("duration", "When does the cover start and end?", {
        "da": ["Hvornår begynder og slutter dækningen?"],
        "de": ["Wann beginnt und endet der Versicherungsschutz?"],
        "en": ["When does the cover start and end?"],
        "fr": ["Quand commence et quand se termine la couverture"],
        "nl": ["Wanneer begint en eindigt de dekking?"]}, verified={"en"}),
    Section("cancel", "How do I cancel the contract?", {
        "da": ["Hvordan opsiger jeg aftalen?"],
        "de": ["Wie kann ich den Vertrag kündigen?"],
        "en": ["How do I cancel the contract?"],
        "fr": ["Comment puis-je résilier le contrat"],
        "nl": ["Hoe zeg ik het contract op?"]}, verified={"en"}),
]


# ── field vocabulary ─────────────────────────────────────────────────────────
# canonical key -> {language: [surface forms]}. Order within a list is irrelevant;
# matching is substring-on-folded-text, longest match wins.
FIELDS: dict[str, dict[str, list[str]]] = {
 "price.annual_premium": {
    "da": ["årlig præmie", "årspræmie", "præmie pr. år"],
    "de": ["jahresbeitrag", "jahresprämie", "beitrag pro jahr"],
    "en": ["annual premium", "yearly premium"],
    "fr": ["prime annuelle", "cotisation annuelle"],
    "nl": ["jaarpremie"]},

 "excesses.general": {
    "da": ["selvrisiko"], "de": ["selbstbeteiligung", "selbstbehalt", "eigenanteil"],
    "en": ["excess", "deductible"], "fr": ["franchise"], "nl": ["eigen risico"]},
 "excesses.collision": {
    "da": ["selvrisiko ved kaskoskade", "kaskoselvrisiko"],
    "de": ["selbstbeteiligung vollkasko", "sb vollkasko"],
    "en": ["accidental damage excess", "comprehensive excess", "standard excess"],
    "fr": ["franchise dommages tous accidents"], "nl": ["eigen risico casco"]},
 "excesses.theft": {
    "da": ["selvrisiko ved tyveri", "tyveriselvrisiko"],
    "de": ["selbstbeteiligung teilkasko", "selbstbeteiligung diebstahl"],
    "en": ["theft excess"], "fr": ["franchise vol"], "nl": ["eigen risico diefstal"]},
 "excesses.glass": {
    "da": ["selvrisiko ved glasskade", "forrudeselvrisiko"],
    "de": ["glasbruch selbstbeteiligung", "selbstbeteiligung glas"],
    "en": ["windscreen excess", "glass excess"],
    "fr": ["franchise bris de glace"], "nl": ["eigen risico ruitschade"]},
 "excesses.young_driver": {
    "da": ["fører under 25", "ung fører"],
    "de": ["fahrer unter 25", "junge fahrer"],
    "en": ["young driver excess", "inexperienced driver excess"],
    "fr": ["jeune conducteur"], "nl": ["jonge bestuurder"]},

 "coverage.third_party_liability": {
    "da": ["ansvarsdækning", "ansvarsforsikring"], "de": ["kfz-haftpflicht", "haftpflicht"],
    "en": ["third party liability", "third-party liability"],
    "fr": ["responsabilité civile"], "nl": ["wettelijke aansprakelijkheid", "wa-dekking"]},
 "coverage.comprehensive": {
    "da": ["kasko", "kaskodækning"], "de": ["vollkasko"],
    "en": ["comprehensive cover"], "fr": ["tous risques"], "nl": ["allrisk", "volledig casco"]},
 "coverage.theft": {
    "da": ["tyveri", "røveri"], "de": ["diebstahl", "entwendung"],
    "en": ["theft"], "fr": ["vol"], "nl": ["diefstal"]},
 "coverage.fire": {
    "da": ["brand"], "de": ["brand"], "en": ["fire"], "fr": ["incendie"], "nl": ["brand"]},
 "coverage.windscreen_glass": {
    "da": ["glasskade", "forrude"], "de": ["glasbruch"],
    "en": ["windscreen", "glass breakage"], "fr": ["bris de glace"], "nl": ["ruitschade"]},
 "coverage.vandalism": {
    "da": ["hærværk"], "de": ["vandalismus", "mutwillige beschädigung"],
    "en": ["vandalism", "malicious damage"], "fr": ["vandalisme"], "nl": ["vandalisme"]},
 "coverage.natural_events": {
    "da": ["naturskade", "storm", "hagl"], "de": ["elementarschäden", "sturm", "hagel"],
    "en": ["storm", "flood", "hail"], "fr": ["événements naturels", "tempête", "grêle"],
    "nl": ["natuurgeweld", "storm", "hagel"]},
 "coverage.roadside_assistance": {
    "da": ["vejhjælp"], "de": ["schutzbrief", "pannenhilfe"],
    "en": ["breakdown assistance", "roadside assistance", "breakdown cover"],
    "fr": ["assistance", "dépannage"], "nl": ["pechhulp", "hulpdienst"]},
 "coverage.legal_assistance": {
    "da": ["retshjælp"], "de": ["verkehrsrechtsschutz", "rechtsschutz"],
    "en": ["legal expenses", "legal protection"],
    "fr": ["protection juridique", "défense pénale et recours"], "nl": ["rechtsbijstand"]},
 "coverage.replacement_vehicle": {
    "da": ["erstatningsbil", "lånebil"], "de": ["mietwagen", "ersatzwagen", "leihwagen"],
    "en": ["courtesy car", "replacement vehicle", "replacement car"],
    "fr": ["véhicule de remplacement"], "nl": ["vervangend vervoer", "leenauto"]},
 "coverage.personal_accident": {
    "da": ["førerulykkesforsikring", "personskade"],
    "de": ["fahrerschutz", "insassenunfall"],
    "en": ["personal accident", "driver injury"],
    "fr": ["garantie du conducteur"], "nl": ["schadeverzekering inzittenden", "svi"]},
 "coverage.foreign_travel": {
    "da": ["udlandsdækning", "i europa", "udenfor danmark"],
    "de": ["auslandsschadenschutz", "im ausland"],
    "en": ["cover in the eu", "driving abroad", "cover abroad"],
    "fr": ["à l'étranger"], "nl": ["buitenland"]},

 "territories": {
    "da": ["dækningsområde", "geografisk område"], "de": ["geltungsbereich"],
    "en": ["territorial limits", "where am i covered"],
    "fr": ["étendue géographique"], "nl": ["dekkingsgebied"]},
 "no_claims": {
    "da": ["skadefri kørsel", "anciennitet", "bonus"],
    "de": ["schadenfreiheitsrabatt", "sf-klasse", "sfr"],
    "en": ["no claims discount", "no claims bonus"],
    "fr": ["bonus-malus", "coefficient de réduction-majoration"],
    "nl": ["schadevrije jaren", "no-claim"]},
}


def fold(s: str) -> str:
    """Case- and accent-insensitive form for matching. Keeps æøå distinguishable
    from ae/oe/aa only insofar as NFKD lets it — sufficient for substring matching."""
    s = unicodedata.normalize("NFKD", s.casefold())
    return "".join(c for c in s if not unicodedata.combining(c))


_FOLDED = {k: {lang: [(fold(t), t) for t in terms] for lang, terms in langs.items()}
           for k, langs in FIELDS.items()}


def match_all(text: str, lang: str | None = None) -> dict[str, int]:
    """Every canonical key the text touches, with the length of its longest hit.

    One clause routinely carries a benefit AND a scope. "Vejhjælp i Europa er
    omfattet af dækningen" is roadside assistance (the benefit) *and* foreign
    travel (its territorial scope) — collapsing it to one key loses half the
    meaning, which is why this returns a set rather than a winner.
    """
    hay = fold(text)
    hits: dict[str, int] = {}
    for key, langs in _FOLDED.items():
        for lg, terms in langs.items():
            if lang and lg != lang:
                continue
            for folded, _orig in terms:
                if folded in hay and len(folded) > hits.get(key, 0):
                    hits[key] = len(folded)
    return hits


def match_field(text: str, lang: str | None = None) -> str | None:
    """The single best key: longest surface form wins, so 'selvrisiko ved tyveri'
    beats 'selvrisiko'. Ties break toward the more specific key (the one declared
    later, since the general forms are declared first). Prefer match_all when a
    clause may carry more than one meaning."""
    hits = match_all(text, lang)
    if not hits:
        return None
    order = list(_FOLDED)
    return max(hits.items(), key=lambda kv: (kv[1], order.index(kv[0])))[0]


def match_section(heading: str) -> str | None:
    hay = fold(heading)
    for sec in SECTIONS:
        for terms in sec.terms.values():
            if any(fold(t).rstrip("?") in hay for t in terms):
                return sec.key
    return None


def verification_state() -> dict[str, object]:
    """What this table still owes the corpus.

    Only English section headings are verified so far — from the Aviva Ireland motor
    IPID. Every Danish, German, French and Dutch term below is a translation we
    believe in, not one we have seen in a published document. The corpus exists to
    settle that, and a term still unverified after the run is a gap to report, not
    a detail to leave quiet.
    """
    langs = ("da", "de", "en", "fr", "nl")
    sec_total = len(SECTIONS) * len(langs)
    sec_done = sum(len(s.verified) for s in SECTIONS)
    field_pairs = sum(len(v) for v in FIELDS.values())
    return {
        "sections_verified": f"{sec_done}/{sec_total}",
        "sections_unverified_by_language": {
            lg: [s.key for s in SECTIONS if lg not in s.verified] for lg in langs},
        "field_language_pairs": field_pairs,
        "field_pairs_verified": 0,
        "note": "verification is set by tools/score_extraction.py once a real document confirms a term",
    }
