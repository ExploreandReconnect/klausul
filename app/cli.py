"""One-shot extraction, for checking the Nebius path works.

    python -m app.cli demo/Fornyelse_2026.pdf
"""
from __future__ import annotations

import json
import sys
import time

from dotenv import load_dotenv

from .extract import extract


def main() -> int:
    load_dotenv()
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    t = time.perf_counter()
    policy = extract(sys.argv[1])
    took = time.perf_counter() - t

    filled = sum(
        1 for f in list(policy.coverage.values()) + list(policy.excesses.values())
        + [policy.price.annual_premium, policy.territories] if f.usable
    )
    print(json.dumps(policy.model_dump(), indent=2, ensure_ascii=False, default=str))
    print(f"\n{filled} fields extracted in {took:.1f}s", file=sys.stderr)
    for u in policy.uncertainties:
        print(f"  uncertain: {u}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
