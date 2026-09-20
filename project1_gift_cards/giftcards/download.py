"""Download the Amazon 2023 Gift Cards review corpus."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

from . import config


def download_raw(force: bool = False) -> Path:
    """Fetch the raw Gift_Cards.jsonl.gz if not already present locally.

    Returns the local path to the gzip file. Uses the source configured in
    config.DATA_URL (cmcauley lab verified working).
    """
    target = config.RAW_GZ
    if target.exists() and not force:
        return target

    import urllib.request

    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {config.DATA_URL}")
    req = urllib.request.Request(
        config.DATA_URL, headers={"User-Agent": "hermes-mbax6418/1.0"}
    )
    with urllib.request.urlopen(req, timeout=120) as resp, open(target, "wb") as out:
        while True:
            chunk = resp.read(1 << 20)  # 1 MB
            if not chunk:
                break
            out.write(chunk)
    print(f"Saved {target} ({target.stat().st_size/1e6:.2f} MB)")
    return target


def review_count(path: Path | None = None) -> int:
    """Count records in a compressed jsonl file."""
    src = path or config.RAW_GZ
    n = 0
    with gzip.open(src, "rt", encoding="utf-8") as f:
        for _ in f:
            n += 1
    return n


def load_reviews(path: Path | None = None) -> list[dict]:
    """Load all review records from a compressed jsonl into a list of dicts."""
    src = path or config.RAW_GZ
    out = []
    with gzip.open(src, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                out.append(json.loads(line))
    return out
