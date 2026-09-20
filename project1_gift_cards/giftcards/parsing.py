"""Robust extraction of a JSON object from a model-generated string."""

from __future__ import annotations

import json
import re


def extract_json_object(raw: str):
    """Return the parsed JSON *object* embedded in `raw` (tolerant parsing).

    Handles markdown code fences and surrounding prose. Only JSON objects are
    returned; a JSON array or scalar raises ValueError. Raises ValueError if no
    recoverable object is found.
    """
    if raw is None:
        raise ValueError("empty model response")
    text = str(raw).strip()

    # Markdown fences first.
    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        obj = _load(fence.group(1))
        if isinstance(obj, dict):
            return obj
        raise ValueError("fenced content is not a JSON object")

    # Try the whole thing.
    try:
        obj = _load(text)
    except ValueError:
        obj = None
    if isinstance(obj, dict):
        return obj

    # Fall back to the first balanced {...} object span.
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            obj = _load(text[start : end + 1])
        except ValueError:
            obj = None
        if isinstance(obj, dict):
            return obj

    raise ValueError(f"could not parse a JSON object from: {raw[:200]!r}")


def _load(s: str):
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        # Strip any trailing commas (common LLM artifact) and retry once.
        cleaned = re.sub(r",\s*([}\]])", r"\1", s)
        return json.loads(cleaned)
