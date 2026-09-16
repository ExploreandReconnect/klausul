"""Measure extraction against hand-labelled ground truth.

    python tools/score_extraction.py --make-labels      # write the blank label sheet
    python tools/score_extraction.py                    # run + score
    python tools/score_extraction.py --market DK

The number this produces is the only thing that makes "≥90% extraction accuracy"
a fact rather than a claim. It is deliberately harsh in three ways:

  * a value that is right but carries NO source quote scores as wrong, because the
    product's promise is traceability, not luck;
  * `not_found` is scored as a distinct outcome, never as a miss — the product is
    allowed to say it could not tell, and is only wrong if the label says the
    document did state it;
  * a WRONG value scores worse than a missing one in the summary, because a
    confident wrong figure is the failure that would actually hurt a consumer.

Label sheet columns:
    doc_id, field, true_value, unit, true_status, page, note
`true_status` is one of explicit / ambiguous / not_in_document.
Leave `true_value` blank when `true_status` is not_in_document.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.schema import DIMENSIONS, Status          # noqa: E402
from app.vocab import parse_amount                 # noqa: E402

REG = ROOT / "corpus" / "register.yaml"
LABELS = ROOT / "corpus" / "labels" / "labels.csv"
OUT = ROOT / "corpus" / "labels" / "scored.json"

FIELDS = [d.path for d in DIMENSIONS]
TOL = 0.005          # 0.5% — covers rounding, not a different figure


def local_docs(market: str | None):
    reg = yaml.safe_load(REG.read_text(encoding="utf-8"))
    for s in reg["sources"]:
        if s.get("doc_type") == "template":
            continue
        if market and s.get("market") != market:
            continue
        if s.get("local") and (ROOT / s["local"]).exists():
            yield s


def make_labels(market: str | None) -> int:
    docs = list(local_docs(market))
    if not docs:
        print("No downloaded documents. Run tools/fetch_corpus.py first.")
        return 1
    LABELS.parent.mkdir(parents=True, exist_ok=True)
    existing = set()
    if LABELS.exists():
        with LABELS.open(encoding="utf-8") as fh:
            existing = {(r["doc_id"], r["field"]) for r in csv.DictReader(fh)}
    rows = [{"doc_id": d["id"], "field": f, "true_value": "", "unit": "",
             "true_status": "", "page": "", "note": ""}
            for d in docs for f in FIELDS if (d["id"], f) not in existing]
    mode = "a" if LABELS.exists() else "w"
    with LABELS.open(mode, newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["doc_id","field","true_value","unit",
                                           "true_status","page","note"])
        if mode == "w":
            w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} new rows → {LABELS.relative_to(ROOT)}")
    print(f"{len(docs)} documents × {len(FIELDS)} fields. "
          f"Fill true_status for every row; leave true_value blank for not_in_document.")
    return 0


def judge(pred, label) -> str:
    """One of: correct, correct_unsourced, wrong, missed, false_positive,
    correct_absence. The taxonomy is the point — a single accuracy number hides
    which failure you have."""
    ts = (label["true_status"] or "").strip()
    tv = (label["true_value"] or "").strip()

    if ts == "not_in_document":
        return "correct_absence" if pred["status"] == Status.NOT_FOUND else "false_positive"

    if pred["status"] == Status.NOT_FOUND:
        return "missed"

    pv, market = pred.get("value"), label.get("_market")
    if tv == "":
        return "wrong"

    a, b = parse_amount(str(pv), market), parse_amount(tv, market)
    if a is not None and b is not None:
        ok = abs(a - b) <= max(abs(b) * TOL, 0.01)
    else:
        ok = str(pv).strip().casefold() == tv.casefold()

    if not ok:
        return "wrong"
    return "correct" if pred.get("source_text") else "correct_unsourced"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--make-labels", action="store_true")
    ap.add_argument("--market")
    a = ap.parse_args()

    if a.make_labels:
        return make_labels(a.market)

    if not LABELS.exists():
        print("No labels. Run --make-labels, then fill the sheet.")
        return 1

    with LABELS.open(encoding="utf-8") as fh:
        labels = list(csv.DictReader(fh))
    unfilled = [r for r in labels if not (r["true_status"] or "").strip()]
    if unfilled:
        print(f"{len(unfilled)} of {len(labels)} rows unlabelled — scoring only the rest.")
    labels = [r for r in labels if (r["true_status"] or "").strip()]
    if not labels:
        return 1

    from app.extract import extract

    docs = {d["id"]: d for d in local_docs(a.market)}
    by_doc = defaultdict(list)
    for r in labels:
        if r["doc_id"] in docs:
            r["_market"] = docs[r["doc_id"]]["market"]
            by_doc[r["doc_id"]].append(r)

    verdicts, per_field, per_market, rows = Counter(), defaultdict(Counter), defaultdict(Counter), []
    for doc_id, rs in by_doc.items():
        d = docs[doc_id]
        print(f"extracting {doc_id} ({d['market']}, {d.get('language')}) …", flush=True)
        try:
            policy = extract(ROOT / d["local"], market=d["market"])
        except Exception as e:
            print(f"  FAILED: {e.__class__.__name__}: {e}")
            verdicts["extract_failed"] += len(rs)
            continue
        for r in rs:
            f = policy.get(r["field"])
            pred = {"value": f.value, "status": f.status, "source_text": f.source_text,
                    "page": f.source_page, "confidence": f.confidence}
            v = judge(pred, r)
            verdicts[v] += 1
            per_field[r["field"]][v] += 1
            per_market[d["market"]][v] += 1
            rows.append({"doc": doc_id, "market": d["market"], "field": r["field"],
                         "verdict": v, "true": r["true_value"], "pred": str(f.value),
                         "status": str(f.status), "conf": f.confidence})

    good = verdicts["correct"] + verdicts["correct_absence"]
    total = sum(verdicts.values())
    print("\n── verdicts ─────────────────────────────")
    for k, n in verdicts.most_common():
        print(f"  {k:<20} {n:>4}  {n/total:6.1%}")
    print(f"\n  SOURCED ACCURACY     {good}/{total} = {good/total:.1%}   (target ≥90%)")
    print(f"  wrong values         {verdicts['wrong']:>4}  ← the failure that hurts a consumer")
    print(f"  unsourced but right  {verdicts['correct_unsourced']:>4}  ← counted as failures by design")

    print("\n── by market ────────────────────────────")
    for m, c in per_market.items():
        t = sum(c.values()); g = c["correct"] + c["correct_absence"]
        print(f"  {m}  {g}/{t} = {g/t:6.1%}")

    print("\n── weakest fields ───────────────────────")
    ranked = sorted(per_field.items(),
                    key=lambda kv: (kv[1]["correct"] + kv[1]["correct_absence"]) / max(sum(kv[1].values()), 1))
    for f, c in ranked[:8]:
        t = sum(c.values()); g = c["correct"] + c["correct_absence"]
        print(f"  {f:<42} {g}/{t} = {g/t:6.1%}")

    OUT.write_text(json.dumps({"verdicts": dict(verdicts),
                               "per_market": {k: dict(v) for k, v in per_market.items()},
                               "per_field": {k: dict(v) for k, v in per_field.items()},
                               "rows": rows}, indent=2), encoding="utf-8")
    print(f"\ndetail → {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
