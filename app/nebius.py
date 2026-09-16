"""Nebius Token Factory client.

Token Factory is OpenAI-API compatible, so the official openai SDK works against it
with a different base_url. The model is an NVIDIA open model (Nemotron 3).
"""
from __future__ import annotations

import json
import os
from typing import Any

BASE_URL = os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1")

# Extraction is the load-bearing step, so it gets the larger reasoning model.
# Explanation is short-form prose and runs on the small one.
MODEL_EXTRACT = os.getenv("KLAUSUL_MODEL_EXTRACT", "nvidia/nemotron-3-super-120b-a12b")
MODEL_EXPLAIN = os.getenv("KLAUSUL_MODEL_EXPLAIN", "nvidia/nemotron-3-nano-30b-a3b")


def client():
    """Imported lazily: reading a PDF, merging labels or scoring should not require
    the openai package, and a missing key should not break tools that never call out."""
    from openai import OpenAI

    key = os.getenv("NEBIUS_API_KEY")
    if not key:
        raise RuntimeError(
            "NEBIUS_API_KEY is not set. Copy .env.example to .env and put your "
            "Token Factory key in it."
        )
    return OpenAI(base_url=BASE_URL, api_key=key)


def complete(system: str, user: str, *, model: str, json_mode: bool = False,
             temperature: float = 0.0, max_tokens: int = 8000) -> str:
    kwargs: dict[str, Any] = dict(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = client().chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""


def complete_json(system: str, user: str, *, model: str = MODEL_EXTRACT,
                  max_tokens: int = 8000) -> dict:
    raw = complete(system, user, model=model, json_mode=True, max_tokens=max_tokens)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start >= 0 and end > start:
            return json.loads(raw[start:end + 1])
        raise
