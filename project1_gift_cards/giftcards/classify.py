"""LLM classification via an OpenAI-compatible endpoint.

Only the review TEXT is sent to the model (star rating is never an input).
Batching is concurrent with bounded retries. Results preserve every original
field plus the model's classification and a status marker.
"""

from __future__ import annotations

import concurrent.futures as cf
import json
import time
from pathlib import Path
from typing import Callable

import openai

from . import config
from .prompts import build_messages, parse_classification


def get_client() -> openai.OpenAI:
    """Construct the OpenAI-compatible client from environment/config."""
    return openai.OpenAI(
        base_url=config.openai_base_url(),
        api_key=config.openai_api_key(),
        timeout=60.0,
        max_retries=2,
    )


def _call_model(
    client: openai.OpenAI,
    messages: list[dict],
    model: str | None,
    use_responses_format: bool = True,
) -> str:
    kwargs = {"model": model, "messages": messages}
    if use_responses_format and config.use_responses_format():
        kwargs["response_format"] = {"type": "json_object"}
    try:
        resp = client.chat.completions.create(**kwargs)
    except Exception:
        # Some OpenAI-compatible servers (e.g. vLLM without a JSON grammar)
        # reject response_format. Fall back to prompt-instructed JSON.
        if "response_format" in kwargs:
            kwargs.pop("response_format")
            resp = client.chat.completions.create(**kwargs)
        else:
            raise
    content = resp.choices[0].message.content
    if not content:
        raise RuntimeError("empty model response")
    return content


def classify_one(
    review: dict,
    client: openai.OpenAI,
    model: str | None = None,
    retries: int = 2,
) -> dict:
    """Classify a single review, returning review + classification fields.

    On final failure the record is returned with status='error' and the error
    message, so a partial batch is never lost.
    """
    model = model or config.default_model()
    out = dict(review)
    last_err = None
    for attempt in range(retries + 1):
        try:
            raw = _call_model(client, build_messages(review), model)
            parsed = parse_classification(raw)
            out.update(parsed)
            out["status"] = "ok"
            out["model"] = model
            return out
        except Exception as e:  # noqa: BLE001 - capture any transient failure
            last_err = e
            if attempt < retries:
                time.sleep(0.5 * (2**attempt))
    out["status"] = "error"
    out["error"] = str(last_err)
    return out


def classify_batch(
    reviews: list[dict],
    client: openai.OpenAI,
    model: str | None = None,
    max_workers: int | None = None,
    progress: Callable[[int, int], None] | None = None,
    max_reviews: int | None = None,
) -> list[dict]:
    """Classify many reviews concurrently. Preserves input order."""
    inputs = reviews if max_reviews is None else reviews[:max_reviews]
    total = len(inputs)
    workers = max_workers or config.max_concurrency()
    results: list[dict] = [None] * total  # type: ignore[list-item]

    def worker(i):
        r = classify_one(inputs[i], client, model)
        return i, r

    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(worker, i) for i in range(total)]
        done = 0
        for fut in cf.as_completed(futs):
            i, r = fut.result()
            results[i] = r
            done += 1
            if progress:
                progress(done, total)

    return [r for r in results if r is not None]


def results_to_jsonl(results: list[dict], path: Path | None = None) -> Path:
    """Persist classified results as gitignored JSONL in data/processed."""
    target = path or config.PROCESSED_DIR / "classified_sample.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, default=str) + "\n")
    return target


def results_to_csv(results: list[dict], path: Path | None = None) -> Path:
    """Persist classified results as CSV (a compact set of columns)."""
    import csv

    target = path or config.PROCESSED_DIR / "classified_sample.csv"
    cols = [
        "rating", "title", "text", "verified_purchase", "helpful_vote",
        "timestamp", "asin", "parent_asin", "user_id",
        "sentiment", "primary_emotion", "sentiment_confidence",
        "emotion_confidence", "evidence", "status", "model",
    ]
    with open(target, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in results:
            w.writerow(r)
    return target
