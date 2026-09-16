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
MODEL_EXPLAIN = os.getenv("KLAUSUL_MODEL_EXPLAIN", "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B")


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


class ModelOutputError(RuntimeError):
    """The model answered, but not with usable JSON.

    This is deliberately NOT a ValueError. json.JSONDecodeError is one, and so is the
    error read_pdf raises for a scanned document — catching them together once made the
    API tell a user their PDF had no text layer when in fact the model had misbehaved.
    Two different failures deserve two different answers.
    """

    def __init__(self, message: str, *, model: str, raw: str, position: int | None = None):
        super().__init__(message)
        self.model = model
        self.position = position
        self.excerpt = _around(raw, position)
        self.raw_chars = len(raw)


def _around(raw: str, position: int | None, width: int = 220) -> str:
    """The text either side of the break, so the failure can be read rather than guessed."""
    if position is None:
        return raw[:width * 2]
    lo = max(0, position - width)
    return raw[lo:position] + " ⟨HERE⟩ " + raw[position:position + width]


def _strip_reasoning(raw: str) -> str:
    """Nemotron is a reasoning model. json_mode is meant to suppress the scratchpad, but
    a stray <think> block would make the whole response unparseable, so it is removed."""
    for open_tag, close_tag in (("<think>", "</think>"), ("<reasoning>", "</reasoning>")):
        while (i := raw.find(open_tag)) >= 0:
            j = raw.find(close_tag, i)
            if j < 0:
                return raw[:i].strip()
            raw = raw[:i] + raw[j + len(close_tag):]
    return raw.strip()


def _loads(raw: str) -> dict:
    """Parse, then fall back to the outermost brace pair before giving up."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start >= 0 and end > start:
            return json.loads(raw[start:end + 1])
        raise


REPAIR = (
    "Your previous reply was not valid JSON. Return the SAME content again as a single "
    "valid JSON object and nothing else. Do not add commentary, markdown fences or "
    "explanation. Escape every quote and newline inside string values. Do not shorten or "
    "change any value: the verbatim quotes must survive exactly as they were."
)


def complete_json(system: str, user: str, *, model: str = MODEL_EXTRACT,
                  max_tokens: int = 8000) -> dict:
    raw = _strip_reasoning(complete(system, user, model=model, json_mode=True,
                                    max_tokens=max_tokens))
    try:
        return _loads(raw)
    except json.JSONDecodeError as first:
        first_pos = first.pos          # bound now: Python unbinds `first` after the block

    # One repair attempt. Cheap relative to re-reading the document, and the failure is
    # usually an unescaped quote inside a verbatim citation rather than a wrong answer.
    try:
        repaired = _strip_reasoning(complete(
            system + "\n\n" + REPAIR, user, model=model, json_mode=True,
            max_tokens=max_tokens))
        return _loads(repaired)
    except json.JSONDecodeError as second:
        raise ModelOutputError(
            f"{model} returned malformed JSON twice ({second.msg} at character {second.pos})",
            model=model, raw=repaired, position=second.pos) from second
    except ModelOutputError:
        raise
    except Exception as exc:                      # a transport failure on the retry
        raise ModelOutputError(
            f"{model} returned malformed JSON, and the repair attempt failed "
            f"({exc.__class__.__name__})",
            model=model, raw=raw, position=first_pos) from exc
