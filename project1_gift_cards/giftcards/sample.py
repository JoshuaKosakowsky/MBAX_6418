"""Stratified sampling of the corpus by star rating.

Default classifier runs use a representative sample stratified on `rating`
to keep API cost/time reasonable (see AGENTS.md costing strategy). The full
corpus is always supported via ``size=None``.
"""

from __future__ import annotations

import random
from pathlib import Path

from . import config


def stratified_sample(
    reviews: list[dict],
    size: int | None,
    seed: int | None = None,
) -> list[dict]:
    """Return a sample stratified by star rating.

    size=None -> return all reviews (full batch). Otherwise take a proportionate
    per-rating subsample so each star class is represented in the sample.
    """
    if size is None or size >= len(reviews):
        return list(reviews)

    rng = random.Random(seed)
    buckets: dict[float, list[dict]] = {}
    for r in reviews:
        buckets.setdefault(float(r.get("rating", 0.0)), []).append(r)

    # Proportion of each rating in the corpus.
    total = len(reviews)
    sample: list[dict] = []
    remaining = size
    for rating, items in sorted(buckets.items()):
        share = len(items) / total
        n = int(round(share * size)) if remaining > 0 else 0
        if remaining > 0:
            n = min(n, remaining, len(items))
        sample.extend(rng.sample(items, n))
        remaining -= n

    # Fill any leftover slots with random extras from all buckets.
    if remaining > 0:
        pool = [r for r in reviews if r not in sample]
        sample.extend(rng.sample(pool, min(remaining, len(pool))))

    rng.shuffle(sample)
    return sample


def split_train_test(
    reviews: list[dict], test_frac: float = 0.2, seed: int | None = None
) -> tuple[list[dict], list[dict]]:
    """Deterministic train/test split on the sampled reviews."""
    rng = random.Random(seed)
    idx = list(range(len(reviews)))
    rng.shuffle(idx)
    n_test = int(len(reviews) * test_frac)
    test_idx = set(idx[:n_test])
    train = [r for i, r in enumerate(reviews) if i not in test_idx]
    test = [r for i, r in enumerate(reviews) if i in test_idx]
    return train, test


def save_sample(reviews: list[dict], path: Path | None = None) -> Path:
    """Write sampled reviews to JSONL (gitignored data/samples dir)."""
    target = path or config.SAMPLES_DIR / "sample.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        for r in reviews:
            f.write(__import__("json").dumps(r) + "\n")
    return target
