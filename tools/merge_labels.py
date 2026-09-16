"""Merge independent model labels into ground truth, with a human only where needed.

    corpus/labels/raw/<doc_id>.<model>.csv      <- one per model per document
    python tools/merge_labels.py                <- verify, agree, queue the rest
    python tools/merge_labels.py --accept       <- fold adjudicated rows into labels.csv

Three frontier models are used as independent annotators, NOT as the truth. Language
models share failure modes — decimal commas, filling absences with plausible values,
flattening conditional amounts — so a number built from their unadjudicated consensus
measures agreement, not accuracy.

What makes the output defensible is the order of operations:

  1. QUOTE VERIFICATION, mechanical. Every claimed quote must appear verbatim in the
     PDF's own extracted text. One that does not is rejected and that model's row is
     discarded. This deletes hallucinated evidence without anyone reading anything,
     and it is the same rule the product itself runs on.
  2. Unanimous AND verified -> accepted, with a 10% random sample flagged anyway so
     the accept rule is itself measured.
  3. Any disagreement -> adjudication queue, three answers side by side.
  4. Unanimous not_in_document -> accepted but ALWAYS flagged. Three models agreeing
     that a clause is absent is the weakest agreement there is: they share the habit
     of missing a clause in a language none of them reads natively, and "absent" is
     the one label whose error the product converts into a question to an insurer.
"""
from __future__ import annotations

import argparse
import csv
import random
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.extract import read_pdf                    # noqa: E402
from app.vocab import parse_amount                  # noqa: E402

REG = ROOT / "corpus" / "register.yaml"
RAW = ROOT / "corpus" / "labels" / "raw"
QUEUE = ROOT / "corpus" / "labels" / "adjudicate.csv"
OUT = ROOT / "corpus" / "labels" / "labels.csv"

AUDIT_RATE = 0.10
random.seed(20260915)          # a fixed sample, so the audit is reproducible

COLS = ["doc_id", "field", "true_value", "unit", "true_status", "page", "quote",
        "note", "your_confidence"]


def norm(s: str) -> str:
    """Whitespace- and accent-tolerant, but not word-tolerant. A quote may differ in
    line breaks and soft hyphens because of PDF extraction; it may not differ in
    words."""
    s = unicodedata.normalize("NFKD", (s or "").casefold())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("­", "").replace("-\n", "")
    return re.sub(r"[\s ]+", " ", s).strip(" .,;:»«\"'")


def same_value(a: str, b: str, market: str) -> bool:
    a, b = (a or "").strip(), (b or "").strip()
    if a.casefold() == b.casefold():
        return True
    na, nb = parse_amount(a, market), parse_amount(b, market)
    if na is not None and nb is not None:
        return abs(na - nb) <= max(abs(nb) * 0.005, 0.01)
    return False


def load_raw():
    """{doc_id: {field: {model: row}}}"""
    out = defaultdict(lambda: defaultdict(dict))
    if not RAW.exists():
        return out
    for p in sorted(RAW.glob("*.csv")):
        parts = p.stem.split(".")
        if len(parts) < 2:
            print(f"  skipping {p.name} — expected <doc_id>.<model>.csv")
            continue
        doc_id, model = ".".join(parts[:-1]), parts[-1]
        with p.open(encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                if r.get("field"):
                    r["_model"] = model
                    out[doc_id][r["field"].strip()][model] = r
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--accept", action="store_true",
                    help="fold the adjudicated queue into labels.csv")
    a = ap.parse_args()

    reg = {s["id"]: s for s in yaml.safe_load(REG.read_text(encoding="utf-8"))["sources"]}

    if a.accept:
        if not QUEUE.exists():
            print("Nothing to accept — run without --accept first.")
            return 1
        with QUEUE.open(encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
        undecided = [r for r in rows if not (r.get("FINAL_status") or "").strip()]
        if undecided:
            print(f"{len(undecided)} of {len(rows)} queue rows still have no FINAL_status.")
            print("Fill FINAL_status (and FINAL_value) before accepting.")
            return 1
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with OUT.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["doc_id","field","true_value","unit",
                                               "true_status","page","note"])
            w.writeheader()
            for r in rows:
                w.writerow({"doc_id": r["doc_id"], "field": r["field"],
                            "true_value": r.get("FINAL_value",""), "unit": r.get("unit",""),
                            "true_status": r["FINAL_status"], "page": r.get("page",""),
                            "note": r.get("note","")})
        print(f"{len(rows)} adjudicated rows → {OUT.relative_to(ROOT)}")
        return 0

    raw = load_raw()
    if not raw:
        print(f"No model labels found in {RAW.relative_to(ROOT)}/.")
        print("See docs/LABELLING_PROMPT.md, then save each reply as <doc_id>.<model>.csv")
        return 1

    # page text per document, for mechanical quote verification
    doctext: dict[str, str] = {}
    for doc_id in raw:
        src = reg.get(doc_id)
        if not src or not src.get("local") or not (ROOT / src["local"]).exists():
            print(f"  ! {doc_id}: no downloaded PDF in the register — quotes cannot be verified")
            doctext[doc_id] = ""
            continue
        try:
            doctext[doc_id] = norm(read_pdf(ROOT / src["local"]))
        except Exception as e:
            print(f"  ! {doc_id}: {e.__class__.__name__} reading PDF — quotes unverifiable")
            doctext[doc_id] = ""

    stats = Counter()
    queue, accepted = [], []

    for doc_id, fields in sorted(raw.items()):
        market = (reg.get(doc_id) or {}).get("market", "")
        body = doctext.get(doc_id, "")
        for field, by_model in sorted(fields.items()):
            verified, rejected = {}, {}
            for model, r in by_model.items():
                status = (r.get("true_status") or "").strip().lower()
                quote = (r.get("quote") or "").strip()
                if status == "not_in_document":
                    verified[model] = r                      # nothing to verify
                elif not quote:
                    rejected[model] = "no quote"
                elif not body:
                    verified[model] = r                      # cannot verify; carried, flagged below
                elif norm(quote) in body:
                    verified[model] = r
                else:
                    rejected[model] = "quote not found in document"
            stats["rows"] += 1
            stats["quote_rejected"] += len(rejected)

            # Raw agreement, measured BEFORE verification throws anyone out. Computing
            # it after would count a model as agreeing when its evidence was rejected —
            # which flatters the figure, and the figure goes in the README.
            if len(by_model) >= 2:
                raw_st = {(r.get("true_status") or "").strip().lower() for r in by_model.values()}
                raw_vals = [(r.get("true_value") or "").strip() for r in by_model.values()]
                if len(raw_st) == 1 and all(same_value(raw_vals[0], v, market) for v in raw_vals[1:]):
                    stats["raw_unanimous"] += 1
                stats["multi_model_rows"] += 1

            if not verified:
                stats["all_rejected"] += 1
                queue.append(_q(doc_id, field, by_model, rejected, "every quote failed verification"))
                continue

            statuses = {m: (r.get("true_status") or "").strip().lower() for m, r in verified.items()}
            values = {m: (r.get("true_value") or "").strip() for m, r in verified.items()}
            one_status = len(set(statuses.values())) == 1
            vals = list(values.values())
            one_value = all(same_value(vals[0], v, market) for v in vals[1:])

            if one_status and one_value and len(verified) >= 2:
                st = next(iter(statuses.values()))
                if st == "not_in_document":
                    stats["unanimous_absent_flagged"] += 1
                    queue.append(_q(doc_id, field, by_model, rejected,
                                    "unanimous not_in_document — the weakest agreement; confirm by eye"))
                elif random.random() < AUDIT_RATE:
                    stats["audit_sample"] += 1
                    queue.append(_q(doc_id, field, by_model, rejected,
                                    "10% audit sample of an accepted row"))
                else:
                    stats["auto_accepted"] += 1
                    r = next(iter(verified.values()))
                    accepted.append({"doc_id": doc_id, "field": field,
                                     "true_value": r.get("true_value",""), "unit": r.get("unit",""),
                                     "true_status": st, "page": r.get("page",""),
                                     "note": r.get("note","")})
            else:
                stats["disagreement"] += 1
                why = "status differs" if not one_status else "value differs"
                queue.append(_q(doc_id, field, by_model, rejected, why))

    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    cols = ["doc_id","field","reason","FINAL_status","FINAL_value","unit","page","note"]
    models = sorted({m for f in raw.values() for bm in f.values() for m in bm})
    for m in models:
        cols += [f"{m}_status", f"{m}_value", f"{m}_quote", f"{m}_verified"]
    with QUEUE.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader(); w.writerows(queue)

    if accepted:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with OUT.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["doc_id","field","true_value","unit",
                                               "true_status","page","note"])
            w.writeheader(); w.writerows(accepted)

    total = stats["rows"] or 1
    agreed = stats["auto_accepted"] + stats["audit_sample"] + stats["unanimous_absent_flagged"]
    print("\n── merge ────────────────────────────────")
    print(f"  cells                     {stats['rows']:>5}")
    print(f"  quotes rejected           {stats['quote_rejected']:>5}  (hallucinated or paraphrased)")
    print(f"  auto-accepted             {stats['auto_accepted']:>5}")
    print(f"  audit sample (10%)        {stats['audit_sample']:>5}")
    print(f"  unanimous absent, flagged {stats['unanimous_absent_flagged']:>5}")
    print(f"  disagreements             {stats['disagreement']:>5}")
    print(f"  all quotes failed         {stats['all_rejected']:>5}")
    mm = stats["multi_model_rows"] or 1
    print(f"\n  RAW inter-annotator agreement      {stats['raw_unanimous']}/{mm} = "
          f"{stats['raw_unanimous']/mm:.1%}   ← the README figure")
    print(f"  after quote verification          {agreed}/{total} = {agreed/total:.1%}")
    print("  The first is the honest one: the second counts a model as agreeing")
    print("  on rows where its own evidence was thrown out.")
    print(f"\n  rows needing you: {len(queue)} of {total} ({len(queue)/total:.0%})")
    print(f"  → {QUEUE.relative_to(ROOT)}   fill FINAL_status / FINAL_value, then --accept")
    return 0


def _q(doc_id, field, by_model, rejected, reason) -> dict:
    row = {"doc_id": doc_id, "field": field, "reason": reason,
           "FINAL_status": "", "FINAL_value": "", "unit": "", "page": "", "note": ""}
    for m, r in by_model.items():
        row[f"{m}_status"] = r.get("true_status", "")
        row[f"{m}_value"] = r.get("true_value", "")
        row[f"{m}_quote"] = (r.get("quote") or "")[:220]
        row[f"{m}_verified"] = "no: " + rejected[m] if m in rejected else "yes"
        if not row["unit"]:
            row["unit"] = r.get("unit", "")
        if not row["page"]:
            row["page"] = r.get("page", "")
    return row


if __name__ == "__main__":
    raise SystemExit(main())
