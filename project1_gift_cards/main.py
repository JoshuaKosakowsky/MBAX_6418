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

from giftcards import classify, config, dashboard, download, evaluate, eval_dashboard, sample


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


def cmd_evaluate(args):
    """Score the binary classifier on a small batch against rating-derived labels.

    The model classifies text-only (binary prompt); the rating is used ONLY to
    compute the reference afterwards (>=4 POSITIVE, else NEGATIVE).
    """
    from giftcards.prompts import build_binary_messages, parse_binary_classification

    src = Path(args.input) if args.input else config.SAMPLES_DIR / "sample.jsonl"
    if not src.exists():
        sys.exit(f"Input not found: {src}. Run `main.py sample` first.")

    reviews = [json.loads(l) for l in src.open() if l.strip()]
    batch = evaluate.build_eval_batch(reviews, args.size, seed=args.seed)
    print(f"eval batch: {len(batch)} reviews "
          f"({sum(1 for r in batch if evaluate.rating_score_label(r.get('rating'))=='POSITIVE')} "
          f"rating-positive / "
          f"{sum(1 for r in batch if evaluate.rating_score_label(r.get('rating'))=='NEGATIVE')} "
          f"rating-negative)")

    client = classify.get_client()
    model = args.model or config.default_model()
    results = classify.classify_batch(
        batch, client, model=model,
        max_workers=args.concurrency,
        messages_fn=lambda r: build_binary_messages(r.get("title", ""), r.get("text", "")),
        parse_fn=parse_binary_classification,
        checkpoint_path=config.PROCESSED_DIR / "eval_batch.jsonl",
    )
    ok = [r for r in results if r.get("status") == "ok"]
    pairs = []
    for r in ok:
        pairs.append((evaluate.rating_score_label(r.get("rating")), (r.get("label") or "").upper()))
    res = evaluate.score(pairs)
    evaluate.attach_disagreements(res, ok)
    print(evaluate.pretty_report(res))

    out = Path(args.output) if args.output else config.PROCESSED_DIR / "eval_scored.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for r in sorted(ok, key=lambda r: float(r.get("rating") or 0)):
            f.write(json.dumps(r, default=str) + "\n")
    print(f"\nSaved scored batch -> {out}")

    if res.disagreements:
        print(f"\nReviews the model gets WRONG vs the rating ({len(res.disagreements)}):")
        for d in res.disagreements[:args.show_errors]:
            print(f"   {d['rating']}* ref={d['truth']:<8} pred={d['pred']:<8} "
                  f"c={d['confidence']} | {d['title']} :: {d['text'][:70]}")


def cmd_eval_dashboard(args):
    """Build the evaluation-results dashboard (single-file HTML)."""
    src = Path(args.input) if args.input else config.PROCESSED_DIR / "eval_scored.jsonl"
    if not src.exists():
        sys.exit(f"Input not found: {src}. Run `main.py evaluate` first.")
    rows = [json.loads(l) for l in src.open() if l.strip()]
    out = Path(args.output) if args.output else None
    eval_dashboard.build(rows, out_path=out, model=args.model)


def cmd_emotions(args):
    """Compare the LLM primary emotion against the NRC word-list emotion.

    The LLM emotion comes from the extended binary prompt (Step 5); the NRC
    emotion is derived offline from the review text with the bundled lexicon.
    No extra model calls are made here.
    """
    from giftcards import nrc

    src = Path(args.input) if args.input else config.PROCESSED_DIR / "eval_scored.jsonl"
    if not src.exists():
        sys.exit(f"Input not found: {src}. Run `main.py evaluate` first.")
    rows = [json.loads(l) for l in src.open() if l.strip()]
    ok = [r for r in rows if r.get("status") == "ok"]
    lex = nrc.load_lexicon()

    def _llm(r):
        e = r.get("primary_emotion")
        return str(e).lower() if e else None

    llm = [_llm(r) for r in ok]
    nrc_list = [nrc.primary_emotion(r.get("text", ""), lex) for r in ok]
    stats = nrc.compare(llm, nrc_list)

    print(f"Reviews: {len(ok)}")
    print(f"Both-signal pairs : {stats['n']}")
    print(f"Agree             : {stats['agree']}")
    print(f"Disagree          : {stats['disagree']}")
    print(f"Agreement rate    : {stats['agreement_rate']:.1%}")
    print("\nLLM emotion distribution:", stats["llm_distribution"])
    print("NRC  emotion distribution:", stats["nrc_distribution"])

    shown = 0
    for r, l, n in zip(ok, llm, nrc_list):
        if l and n and l != n:
            print(f"  LLM={l:<12} NRC={n:<12} | {str(r.get('title') or '')[:28]} :: {(r.get('text') or '')[:64]}")
            shown += 1
            if shown >= (args.show or 40):
                break
    if shown == 0:
        print("\nNo divergences to show.")

    out = Path(args.output) if args.output else config.PROCESSED_DIR / "emotion_compare.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for r, n in zip(ok, nrc_list):
            rr = dict(r)
            rr["primary_emotion"] = _llm(r)
            rr["nrc_emotion"] = n
            f.write(json.dumps(rr, default=str) + "\n")
    print(f"\nSaved -> {out}")


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

    ev = sub.add_parser("evaluate", help="score binary classifier against rating-derived labels")
    ev.add_argument("--input", default=None)
    ev.add_argument("--size", type=int, default=100)
    ev.add_argument("--seed", type=int, default=None)
    ev.add_argument("--model", default=None)
    ev.add_argument("--concurrency", type=int, default=None)
    ev.add_argument("--show-errors", type=int, default=1000)
    ev.add_argument("--output", default=None)
    ev.set_defaults(fn=cmd_evaluate)

    evd = sub.add_parser("eval-dashboard", help="build the evaluation results dashboard")
    evd.add_argument("--input", default=None)
    evd.add_argument("--output", default=None)
    evd.add_argument("--model", default=None)
    evd.set_defaults(fn=cmd_eval_dashboard)

    em = sub.add_parser("emotions", help="compare LLM vs NRC primary emotion")
    em.add_argument("--input", default=None)
    em.add_argument("--show", type=int, default=40)
    em.add_argument("--output", default=None)
    em.set_defaults(fn=cmd_emotions)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
