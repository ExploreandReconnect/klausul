"""Generate the three synthetic demo policies.

These are invented products from invented insurers. They exist so the pipeline can be
demonstrated end to end without uploading anyone's real insurance documents. The
structure follows the IPID section order from Commission Implementing Regulation
(EU) 2017/1469 so the extraction is exercised against a realistic shape.

    python tools/make_demo_pdfs.py
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

OUT = Path(__file__).resolve().parent.parent / "demo"

ss = getSampleStyleSheet()
H = ParagraphStyle("H", parent=ss["Heading2"], fontSize=11.5, spaceAfter=4, spaceBefore=10)
B = ParagraphStyle("B", parent=ss["BodyText"], fontSize=9, leading=12.5)
T = ParagraphStyle("T", parent=ss["Title"], fontSize=15, spaceAfter=2)
S = ParagraphStyle("S", parent=ss["BodyText"], fontSize=8.5, textColor="#555555", spaceAfter=8)


def build(name: str, title: str, sub: str, blocks: list[tuple[str, list[str]]]) -> Path:
    path = OUT / name
    doc = SimpleDocTemplate(str(path), pagesize=A4,
                            leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=18 * mm, bottomMargin=18 * mm, title=title)
    story = [Paragraph(title, T), Paragraph(sub, S)]
    for head, lines in blocks:
        story.append(Paragraph(head, H))
        for ln in lines:
            story.append(Paragraph(ln, B))
        story.append(Spacer(1, 2))
    doc.build(story)
    return path


DA_2025 = [
    ("Hvilken form for forsikring er der tale om?",
     ["Bilforsikring for privat personbil. Ansvarsdækning, kaskodækning og tilvalg."]),
    ("Hvad dækker den?",
     ["Ansvar for personskade: 150.000.000 EUR pr. skade.",
      "Ansvar for tingskade: 10.000.000 EUR pr. skade.",
      "Kasko: skade på egen bil ved sammenstød, væltning og hærværk.",
      "Tyveri og røveri af køretøjet.",
      "Brand, lynnedslag og eksplosion.",
      "Glasskade, herunder forrude.",
      "Retshjælp: dækningssum 100.000 EUR pr. begivenhed.",
      "Vejhjælp i Europa er omfattet af dækningen.",
      "Der stilles erstatningsbil til rådighed i op til 30 dage pr. skadebegivenhed."]),
    ("Hvad dækker den ikke?",
     ["Skade opstået under motorløb eller køreteknisk kursus.",
      "Skade forvoldt med forsæt eller under selvforskyldt beruselse.",
      "Almindeligt slid og mekanisk nedbrud."]),
    ("Er der nogen begrænsninger i dækningen?",
     ["Selvrisiko ved kaskoskade: 400 EUR",
      "Selvrisiko ved tyveri og røveri: 300 EUR",
      "Selvrisiko ved glasskade: 150 EUR",
      "Selvrisiko ved fører under 25 år: 900 EUR"]),
    ("Hvor er jeg dækket?",
     ["Dækningen gælder i EU/EØS samt Schweiz og Storbritannien."]),
    ("Hvornår og hvordan betaler jeg?",
     ["Årlig præmie inkl. afgifter: 720,00 EUR",
      "Betaling sker halvårligt via betalingsservice."]),
    ("Hvornår begynder og slutter dækningen?",
     ["Policen løber fra 01.01.2025 til 31.12.2025 og fornyes automatisk."]),
    ("Hvordan opsiger jeg aftalen?",
     ["Aftalen kan opsiges skriftligt med 30 dages varsel til udløb af en betalingsperiode."]),
]

DA_2026 = [
    ("Hvilken form for forsikring er der tale om?",
     ["Bilforsikring for privat personbil. Ansvarsdækning, kaskodækning og tilvalg."]),
    ("Hvad dækker den?",
     ["Ansvar for personskade: 150.000.000 EUR pr. skade.",
      "Ansvar for tingskade: 10.000.000 EUR pr. skade.",
      "Kasko: skade på egen bil ved sammenstød, væltning og hærværk.",
      "Tyveri og røveri af køretøjet.",
      "Brand, lynnedslag og eksplosion.",
      "Glasskade, herunder forrude.",
      "Retshjælp: dækningssum 150.000 EUR pr. begivenhed.",
      "Der stilles erstatningsbil til rådighed i op til 14 dage pr. skadebegivenhed."]),
    ("Hvad dækker den ikke?",
     ["Skade opstået under motorløb eller køreteknisk kursus.",
      "Skade forvoldt med forsæt eller under selvforskyldt beruselse.",
      "Almindeligt slid og mekanisk nedbrud."]),
    ("Er der nogen begrænsninger i dækningen?",
     ["Selvrisiko ved kaskoskade: 400 EUR",
      "Selvrisiko ved tyveri og røveri: 500 EUR",
      "Selvrisiko ved glasskade: 100 EUR",
      "Selvrisiko ved fører under 25 år: 900 EUR"]),
    ("Hvor er jeg dækket?",
     ["Dækningen gælder i EU/EØS samt Schweiz og Storbritannien."]),
    ("Hvornår og hvordan betaler jeg?",
     ["Årlig præmie inkl. afgifter: 810,00 EUR",
      "Betaling sker halvårligt via betalingsservice."]),
    ("Hvornår begynder og slutter dækningen?",
     ["Policen løber fra 01.01.2026 til 31.12.2026 og fornyes automatisk."]),
    ("Hvordan opsiger jeg aftalen?",
     ["Aftalen kan opsiges skriftligt med 30 dages varsel til udløb af en betalingsperiode."]),
]

DE_OFFER = [
    ("Um welche Art von Versicherung handelt es sich?",
     ["Kraftfahrzeugversicherung für einen privaten Pkw. Haftpflicht, Vollkasko, Teilkasko."]),
    ("Was ist versichert?",
     ["Personenschäden: 150.000.000 EUR je Schadenfall.",
      "Sachschäden: 12.000.000 EUR je Schadenfall.",
      "Vollkasko: Schäden am eigenen Fahrzeug durch Unfall und Vandalismus.",
      "Teilkasko: Diebstahl, Brand, Explosion, Sturm, Hagel und Wildschaden.",
      "Glasbruch: keine Selbstbeteiligung bei Reparatur. Bei Austausch gelten die "
      "Bedingungen in Ziffer 7.3.",
      "Rechtsschutz im Verkehr: 150.000 EUR je Ereignis.",
      "Einzelheiten zum Schutzbrief entnehmen Sie bitte der gesonderten "
      "Leistungsübersicht."]),
    ("Was ist nicht versichert?",
     ["Schäden bei Rennveranstaltungen und Fahrsicherheitstrainings.",
      "Vorsätzlich herbeigeführte Schäden.",
      "Verschleiß und Betriebsschäden."]),
    ("Gibt es Deckungsbeschränkungen?",
     ["Selbstbeteiligung Vollkasko: 700 EUR je Schadenfall",
      "Selbstbeteiligung Teilkasko (Diebstahl): 500 EUR",
      "Selbstbeteiligung für Fahrer unter 25 Jahren: 1.100 EUR",
      "Der Schadenfreiheitsrabatt wird übernommen, jedoch um zwei Stufen zurückgestuft."]),
    ("Wo bin ich versichert?",
     ["Geltungsbereich: Mitgliedstaaten des EWR. Schweiz und Vereinigtes Königreich "
      "sind nicht eingeschlossen."]),
    ("Wann und wie zahle ich?",
     ["Jahresbeitrag inkl. Versicherungsteuer: 684,00 EUR",
      "Zahlung jährlich im Voraus per SEPA-Lastschrift."]),
    ("Wann beginnt und endet der Versicherungsschutz?",
     ["Angebot gültig bis 31.10.2026. Versicherungsbeginn nach Annahme."]),
    ("Wie kann ich den Vertrag kündigen?",
     ["Kündigung in Textform mit einer Frist von einem Monat zum Ablauf."]),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    made = [
        build("Bilforsikring_2025.pdf", "Nordvest Forsikring &ndash; Bilforsikring",
              "Dokument med oplysninger om forsikringsproduktet (IPID) &middot; "
              "Produkt: Bil Plus &middot; Policenr. NV-4471-2025 &middot; "
              "Fuldst&aelig;ndige oplysninger findes i policen og forsikringsbetingelserne.",
              DA_2025),
        build("Fornyelse_2026.pdf", "Nordvest Forsikring &ndash; Fornyelse 2026",
              "Dokument med oplysninger om forsikringsproduktet (IPID) &middot; "
              "Produkt: Bil Plus &middot; Policenr. NV-4471-2026 &middot; "
              "Fuldst&aelig;ndige oplysninger findes i policen og forsikringsbetingelserne.",
              DA_2026),
        build("Angebot_Meridian.pdf", "Meridian Direkt &ndash; Kfz-Versicherung",
              "Informationsblatt zu Versicherungsprodukten (IPID) &middot; "
              "Produkt: Meridian Auto Kompakt &middot; Angebotsnr. MD-88210 &middot; "
              "Die vollst&auml;ndigen Informationen finden Sie in den Vertragsunterlagen.",
              DE_OFFER),
    ]
    for p in made:
        print(f"wrote {p}")
    print("\nThese are invented products from invented insurers, for demonstration only.")


if __name__ == "__main__":
    main()
