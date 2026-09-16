"""FastAPI surface.

POST /compare with two PDFs, a market and a profile; get back the ledger the page
renders. The pipeline order here is the product's whole claim, so it is written out
plainly: extract -> validate -> compare (no model) -> weigh (no model) -> explain.

The page is served from here too, so a single container is the whole product. In
production the page usually comes from GitHub Pages instead and calls this origin
cross-site, which is why CORS is configured rather than assumed.
"""
from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .compare import compare
from .explain import actions, explain_one
from .extract import extract
from .nebius import ModelOutputError
from .relevance import Profile, weigh
from .vocab import NUMBER_FORMATS

load_dotenv()

app = FastAPI(title="Klausul", version="0.2.0")

# The page lives on a different origin in production (GitHub Pages), so it must be
# allowed explicitly. Set KLAUSUL_ALLOWED_ORIGINS to your Pages URL once you have
# it; "*" is the permissive default for a public, unauthenticated demo endpoint.
_origins = [o.strip() for o in os.getenv("KLAUSUL_ALLOWED_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,          # no cookies, no auth — nothing to leak
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

WEB = Path(__file__).resolve().parent.parent / "web"
DEMO = Path(__file__).resolve().parent.parent / "demo"
MAX_BYTES = 12 * 1024 * 1024          # an IPID is two A4 pages; 12 MB is generous

# Every call into the model is synchronous (the openai SDK's blocking client), so it
# must run in a worker thread. Calling it directly from an `async def` handler blocks
# uvicorn's event loop for the whole run, which stops /health answering, which makes
# the platform conclude the service is dead and restart it mid-request. That is not a
# theoretical risk: it is what happened on the first live run.
EXPLAIN_CONCURRENCY = 4               # Token Factory is fine with this; be a good citizen

if WEB.is_dir():
    app.mount("/static", StaticFiles(directory=WEB), name="static")
if DEMO.is_dir():
    app.mount("/demo", StaticFiles(directory=DEMO), name="demo")


@app.get("/")
def index():
    page = WEB / "index.html"
    if not page.exists():
        return JSONResponse({"error": "page not built"}, status_code=404)
    return FileResponse(page)


@app.get("/health")
def health():
    """Render's health check, and an honest readiness signal for the page: it tells
    the front end whether a live run is actually possible before offering one."""
    return {
        "ok": True,
        "live": bool(os.getenv("NEBIUS_API_KEY")),
        "model_extract": os.getenv("KLAUSUL_MODEL_EXTRACT", ""),
        "model_explain": os.getenv("KLAUSUL_MODEL_EXPLAIN", ""),
        "markets": sorted(NUMBER_FORMATS),
    }


def _profile_text(p: Profile) -> str:
    bits = []
    if p.annual_km:
        bits.append(f"{p.annual_km:,} km a year")
    if p.drives_abroad is not None:
        bits.append("drives abroad regularly" if p.drives_abroad else "drives domestically only")
    if p.vehicle_dependency:
        bits.append(f"{p.vehicle_dependency} dependency on the car")
    if p.parking:
        bits.append(f"parks {'on the street' if p.parking == 'street' else 'off-street'}")
    if p.money_preference:
        bits.append(f"prefers {p.money_preference}")
    return "; ".join(bits) or "no circumstances supplied"


async def _save(up: UploadFile, dest: Path) -> None:
    size = 0
    with dest.open("wb") as fh:
        while chunk := await up.read(1 << 20):
            size += len(chunk)
            if size > MAX_BYTES:
                raise HTTPException(413, f"{up.filename} is larger than {MAX_BYTES // 1048576} MB")
            fh.write(chunk)
    if size == 0:
        raise HTTPException(400, f"{up.filename} is empty")


@app.post("/compare")
async def compare_endpoint(
    current: UploadFile = File(..., description="Current or previous policy PDF"),
    other: UploadFile = File(..., description="Renewal or competing offer PDF"),
    market: str = Form(..., description="DK | DE | IE | FR | NL — selects the number convention"),
    mode: str = Form("renewal", description="renewal | offer"),
    profile_json: str = Form("{}"),
):
    if market not in NUMBER_FORMATS:
        raise HTTPException(
            400,
            f"Unknown market {market!r}. Supported: {', '.join(sorted(NUMBER_FORMATS))}. "
            "The number convention cannot be guessed — '2,500' is 2500 in IE and 2.5 in DE.",
        )
    if not os.getenv("NEBIUS_API_KEY"):
        raise HTTPException(503, "NEBIUS_API_KEY is not configured on this server.")

    t0 = time.perf_counter()
    profile = Profile.model_validate_json(profile_json or "{}")
    timings: dict[str, float] = {}

    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for up in (current, other):
            name = Path(up.filename or "upload.pdf").name
            dest = Path(tmp) / name
            await _save(up, dest)
            paths.append(dest)

        t = time.perf_counter()
        try:
            # Off the event loop, and both documents at once. They are independent,
            # so running them in sequence only ever bought us a longer wall clock.
            a, b = await asyncio.gather(
                asyncio.to_thread(extract, paths[0], market=market),
                asyncio.to_thread(extract, paths[1], market=market),
            )
        except ModelOutputError as e:
            # The model misbehaved. Say so, and show what it actually emitted — this
            # product's whole claim is that a failure is visible rather than plausible,
            # which has to hold for its own failures too.
            raise HTTPException(502, {
                "error": "The extraction model did not return usable JSON.",
                "model": e.model,
                "detail": str(e),
                "position": e.position,
                "response_chars": e.raw_chars,
                "excerpt": e.excerpt,
            }) from e
        except ValueError as e:
            # read_pdf raises this for a PDF with no text layer
            raise HTTPException(422, str(e)) from e
        timings["extract"] = time.perf_counter() - t

    t = time.perf_counter()
    result = compare(a, b)
    timings["compare"] = time.perf_counter() - t

    t = time.perf_counter()
    weighted = weigh(result.material, profile)
    timings["weigh"] = time.perf_counter() - t

    ptext = _profile_text(profile)
    t = time.perf_counter()

    sem = asyncio.Semaphore(EXPLAIN_CONCURRENCY)

    async def _explain(w):
        async with sem:
            try:
                return await asyncio.to_thread(explain_one, w, ptext), None
            except Exception as exc:      # an explanation failure must not lose the finding
                return None, f"explanation unavailable: {exc.__class__.__name__}"

    async def _actions():
        try:
            return await asyncio.to_thread(actions, weighted, ptext), None
        except Exception as exc:          # nor may it lose the whole run
            return [], f"actions unavailable: {exc.__class__.__name__}"

    # The action list depends on the findings, not on their explanations, so it is
    # computed alongside them rather than after them.
    *explanations, (acts, acts_note) = await asyncio.gather(
        *(_explain(w) for w in weighted), _actions()
    )

    explained = []
    for w, (e, note) in zip(weighted, explanations):
        explained.append({
            "key": w.difference.key,
            "label": w.difference.label,
            "verdict": w.difference.verdict,
            "relevance": w.relevance,
            "why_relevant": w.reasons,
            "delta": w.difference.delta_text,
            "unit": w.difference.unit,
            "current": w.difference.a.model_dump(mode="json"),
            "other": w.difference.b.model_dump(mode="json"),
            "explanation": e.model_dump() if e else None,
            "note": note,
        })
    timings["explain"] = time.perf_counter() - t

    return JSONResponse({
        "mode": mode,
        "market": market,
        "documents": [
            {"role": "current", "name": current.filename,
             "insurer": a.document.insurer.value, "language": a.document.language.value},
            {"role": "other", "name": other.filename,
             "insurer": b.document.insurer.value, "language": b.document.language.value},
        ],
        "counts": result.counts,
        "differences": explained,
        "actions": acts,
        "actions_note": acts_note,
        "uncertainties": a.uncertainties + b.uncertainties,
        "timings_s": {k: round(v, 2) for k, v in timings.items()},
        "total_s": round(time.perf_counter() - t0, 2),
    })
