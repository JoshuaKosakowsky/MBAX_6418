"""Gift card review sentiment & emotion classifier — command-line interface.

Usage (from this project folder, via uv):
    uv run python main.py download [--force]
    uv run python main.py sample [--size 3000 | --full] [--seed 42]
    uv run python main.py classify [--input data/samples/sample.jsonl]
                                   [--model deepseek-chat] [--limit N]
    uv run python main.py smoke [--limit 10]        # cheap model, quick wiring check
    uv run python main.py dashboard [--input <classified.jsonl>] [--max-rows N]

Pipeline: download -> sample -> classify -> dashboard.
Per AGENTS.md, smoke tests use the cheaper model first and unit tests run with no
network. See tests/.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from giftcards import classify, config, dashboard, download, sample


# --- subcommands ----------------------------------------------------------
def cmd_download(args):
    path = download.download_raw(force=args.force)
    print(f"Reviews on disk: {download.review_count(path)}")


def cmd_sample(args):
    if not config.RAW_GZ.exists():
        download.download_raw()
    reviews = download.load_reviews()
    size = None if args.full else (args.size or config.sample_size())
    out = sample.stratified_sample(reviews, size, seed=args.seed)
    p = sample.save_sample(out)
    print(f"Wrote {len(out)} reviews -> {p}")
    _print_rating_dist(out)


def cmd_classify(args):
    client = classify.get_client()
    src = Path(args.input) if args.input else config.SAMPLES_DIR / "sample.jsonl"
    if not src.exists():
        sys.exit(f"Input not found: {src}. Run `main.py sample` first.")
    reviews = [json.loads(l) for l in src.open() if l.strip()]
    model = args.model or config.default_model()
    print(f"Classifying {len(reviews)} reviews with model {model!r} (limit={args.limit or 'all'})")
    ckpt = config.PROCESSED_DIR / "classified_sample.jsonl"
    results = classify.classify_batch(
        reviews, client, model=model,
        max_workers=args.concurrency, max_reviews=args.limit,
        progress=lambda d, t: print(f"  {d}/{t} done", end="\r"),
        checkpoint_path=ckpt,
    )
    print()
    jl = classify.results_to_jsonl(results)
    csv = classify.results_to_csv(results)
    _report(results)
    print(f"Wrote {jl}\nWrote {csv}")


def cmd_smoke(args):
    """Cheap-model smoke test: verify end-to-end wiring on a small set quickly."""
    client = classify.get_client()
    reviews = [
        {"title": "Great gift", "text": "Having Amazon money is always good.", "rating": 5.0},
        {"title": "Meh", "text": "The card arrived but the design is boring.", "rating": 3.0},
        {"title": "Terrible", "text": "Never received my balance, support is useless.", "rating": 1.0},
    ]
    model = args.model or config.smoke_model()  # cheaper model per AGENTS.md
    print(f"SMOKE: model={model!r} reviews={len(reviews)}")
    results = classify.classify_batch(reviews, client, model=model, max_reviews=args.limit)
    ok = [r for r in results if r.get("status") == "ok"]
    print(f"smoke ok: {len(ok)}/{len(results)}")
    for r in ok:
        print(f"  {r.get('rating')}★ -> {r.get('sentiment')!s:8} / {r.get('primary_emotion')!s:8} conf={r.get('sentiment_confidence')}")
    if len(ok) == 0:
        sys.exit("SMOKE FAILED: no successful classifications")


def cmd_dashboard(args):
    src = Path(args.input) if args.input else _latest_classified()
    if not src.exists():
        sys.exit(f"Input not found: {src}. Run `main.py classify` first.")
    rows = dashboard.load_results_jsonl(src)
    out = dashboard.build_dashboard(rows, max_rows=args.max_rows)
    print(f"Dashboard: {out}")


# --- helpers --------------------------------------------------------------
def _latest_classified() -> Path:
    files = sorted(config.PROCESSED_DIR.glob("classified_sample.jsonl"), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else config.PROCESSED_DIR / "classified_sample.jsonl"


def _report(results):
    ok = [r for r in results if r.get("status") == "ok"]
    err = [r for r in results if r.get("status") == "error"]
    from collections import Counter
    print(f"completed: {len(ok)} ok / {len(err)} error")
    if ok:
        print("sentiment:", dict(Counter(r["sentiment"] for r in ok)))
        print("emotion:  ", dict(Counter(r["primary_emotion"] for r in ok)))


def _print_rating_dist(reviews):
    from collections import Counter
    print("rating dist:", dict(sorted(Counter(float(r.get("rating", 0.0)) for r in reviews).items())))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("download", help="download the Gift_Cards corpus")
    d.add_argument("--force", action="store_true")
    d.set_defaults(fn=cmd_download)

    s = sub.add_parser("sample", help="build a stratified sample")
    s.add_argument("--size", type=int, default=None)
    s.add_argument("--full", action="store_true", help="use the whole corpus")
    s.add_argument("--seed", type=int, default=None)
    s.set_defaults(fn=cmd_sample)

    c = sub.add_parser("classify", help="run classification on a sample")
    c.add_argument("--input", default=None)
    c.add_argument("--model", default=None)
    c.add_argument("--limit", type=int, default=None)
    c.add_argument("--concurrency", type=int, default=None)
    c.set_defaults(fn=cmd_classify)

    sm = sub.add_parser("smoke", help="cheap-model smoke test (AGENTS.md)")
    sm.add_argument("--model", default=None)
    sm.add_argument("--limit", type=int, default=10)
    sm.set_defaults(fn=cmd_smoke)

    db = sub.add_parser("dashboard", help="build the HTML dashboard")
    db.add_argument("--input", default=None)
    db.add_argument("--max-rows", type=int, default=None)
    db.set_defaults(fn=cmd_dashboard)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
