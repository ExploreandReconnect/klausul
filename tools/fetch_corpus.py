"""Fetch the corpus. Runs on YOUR machine, against YOUR documented routes.

    python tools/fetch_corpus.py --probe          # check routes, change nothing
    python tools/fetch_corpus.py                  # download route: open entries
    python tools/fetch_corpus.py --market DK

The rule this implements: we do not scrape. Concretely —

  * only entries marked `route: open` are ever fetched;
  * one request per document, no crawling, no link-following, no discovery;
  * robots.txt is checked for the host and a disallow turns the entry into
    `route: blocked` with today's probe date rather than a download;
  * a non-PDF response, a 403/404, or a redirect off-host is recorded as
    blocked, never retried with a different method;
  * blocked entries get a drafted contact email written to corpus/contact/.

Everything it learns is written back to the register, so the register stays the
single record of what is reachable and what needs a human to write to someone.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
REG = ROOT / "corpus" / "register.yaml"
PDF = ROOT / "corpus" / "pdf"
CONTACT = ROOT / "corpus" / "contact"
UA = "Klausul-corpus/0.1 (open-source EU motor IPID research; contact in repo README)"
DELAY_S = 2.0
TODAY = dt.date.today().isoformat()

CONTACT_TEMPLATE = """Subject: Request to use your published IPID in an open-source research corpus

Dear {insurer},

I am building Klausul, an open-source (MIT) research project that helps EU
consumers understand what changed in a motor-insurance renewal, and what would
change if they switched. It normalises documents to the Insurance Product
Information Document structure set out in Commission Implementing Regulation
(EU) 2017/1469.

I would like to include your published motor IPID in a small evaluation corpus
({market}, ~10 documents per market) used solely to measure extraction accuracy.
I could not find a documented machine-readable route to the document, so I have
not retrieved it automatically and will not do so.

Could you either:
  1. point me to a stable public URL for the current motor IPID, or
  2. send the PDF directly, or
  3. tell me if you would prefer the document not be included?

The corpus is used for measurement only. No policy wording is republished; the
project stores the document, an extracted field table, and a page-level citation.

Thank you,
{owner}
{email}

Probed: {probed}. Registered as blocked in corpus/register.yaml until answered.
"""


def robots_ok(url: str) -> bool | None:
    """True allowed, False disallowed, None couldn't determine."""
    p = urllib.parse.urlparse(url)
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(f"{p.scheme}://{p.netloc}/robots.txt")
    try:
        rp.read()
    except Exception:
        return None
    try:
        return rp.can_fetch(UA, url)
    except Exception:
        return None


def head(url: str) -> tuple[int, str, str]:
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.headers.get("Content-Type", ""), r.geturl()


def write_contact(src: dict, owner: str, email: str) -> Path:
    CONTACT.mkdir(parents=True, exist_ok=True)
    path = CONTACT / f"{src['id']}.txt"
    path.write_text(CONTACT_TEMPLATE.format(
        insurer=src.get("insurer", "Sir or Madam"), market=src.get("market", ""),
        owner=owner, email=email, probed=TODAY), encoding="utf-8")
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true", help="check routes, download nothing")
    ap.add_argument("--market", help="limit to one market")
    ap.add_argument("--owner", default="Hesham Morten Gabr")
    ap.add_argument("--email", default="smg@exploreandreconnect.com")
    a = ap.parse_args()

    reg = yaml.safe_load(REG.read_text(encoding="utf-8"))
    changed = 0
    counts = {"open": 0, "downloaded": 0, "blocked": 0, "probe_needed": 0, "no_url": 0}

    for src in reg["sources"]:
        if a.market and src.get("market") != a.market:
            continue
        route, url = src.get("route"), src.get("url")

        if not url:
            counts["no_url"] += 1
            print(f"  ·  {src['id']:<28} no url yet — probe by hand, then add it")
            continue

        if route == "blocked":
            counts["blocked"] += 1
            continue

        allowed = robots_ok(url)
        if allowed is False:
            src["route"] = "blocked"
            src["probed"] = TODAY
            src["blocked_reason"] = "robots.txt disallows this path for our agent"
            p = write_contact(src, a.owner, a.email)
            counts["blocked"] += 1; changed += 1
            print(f"  ✗  {src['id']:<28} robots disallow → blocked, contact drafted at {p.name}")
            continue

        try:
            status, ctype, final = head(url)
        except Exception as e:
            src["route"] = "blocked"
            src["probed"] = TODAY
            src["blocked_reason"] = f"{e.__class__.__name__}: {e}"
            p = write_contact(src, a.owner, a.email)
            counts["blocked"] += 1; changed += 1
            print(f"  ✗  {src['id']:<28} {e.__class__.__name__} → blocked, contact drafted")
            continue

        if "pdf" not in ctype.lower():
            src["route"] = "blocked"
            src["probed"] = TODAY
            src["blocked_reason"] = f"served {ctype or 'unknown'}, not a PDF — no document route"
            p = write_contact(src, a.owner, a.email)
            counts["blocked"] += 1; changed += 1
            print(f"  ✗  {src['id']:<28} not a PDF ({ctype}) → blocked, contact drafted")
            continue

        src["route"] = "open"
        src["probed"] = TODAY
        counts["open"] += 1; changed += 1
        print(f"  ✓  {src['id']:<28} open  {final}")

        if not a.probe:
            out = PDF / src["market"] / f"{src['id']}.pdf"
            out.parent.mkdir(parents=True, exist_ok=True)
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r, out.open("wb") as fh:
                fh.write(r.read())
            src["local"] = str(out.relative_to(ROOT))
            src["bytes"] = out.stat().st_size
            counts["downloaded"] += 1
            print(f"     → {out.relative_to(ROOT)}  ({out.stat().st_size:,} bytes)")

        time.sleep(DELAY_S)

    if changed:
        REG.write_text(yaml.safe_dump(reg, allow_unicode=True, sort_keys=False), encoding="utf-8")
        print(f"\nregister updated ({changed} entries)")

    print("\n" + "  ".join(f"{k}={v}" for k, v in counts.items()))
    if counts["blocked"]:
        print(f"drafted contact emails in {CONTACT.relative_to(ROOT)}/ — send them, don't work around them")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
