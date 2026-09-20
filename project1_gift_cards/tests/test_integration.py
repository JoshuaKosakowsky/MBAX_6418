"""SMOKE and E2E integration tests.

SMOKE (cheap model first, per AGENTS.md): verifies end-to-end wiring on a tiny
set using the cheaper configured model. E2E: runs the full pipeline on a small
sample. Both require a working `.env` (real endpoint + key); they skip cleanly
otherwise so unit tests stay offline.
"""
import os

import pytest

from giftcards import classify

HAS_CREDS = bool(
    os.environ.get("OPENAI_BASE_URL")
    and os.environ.get("OPENAI_API_KEY")
    and not os.environ["OPENAI_API_KEY"].startswith("sk-your")
)

pytestmark = pytest.mark.skipif(not HAS_CREDS, reason="no .env credentials configured")

TINY = [
    {"title": "Great gift", "text": "Having Amazon money is always good.", "rating": 5.0},
    {"title": "Meh", "text": "The design printed is pretty dull but it works.", "rating": 3.0},
    {"title": "Terrible", "text": "Code never activated, support unresponsive.", "rating": 1.0},
]


@pytest.mark.smoke
def test_smoke_cheap_model():
    """Cheap-model wiring check: get parseable classifications quickly."""
    from giftcards import config

    client = classify.get_client()
    results = classify.classify_batch(TINY, client, model=config.smoke_model(), max_reviews=3)
    ok = [r for r in results if r.get("status") == "ok"]
    assert len(ok) == len(TINY), f"only {len(ok)}/{len(TINY)} succeeded"
    for r in ok:
        assert r["sentiment"] in ("positive", "neutral", "negative")
        assert r["primary_emotion"] in (
            "joy", "sadness", "anger", "fear", "surprise", "disgust", "neutral"
        )
        assert 0.0 <= (r["sentiment_confidence"] or 0.0) <= 1.0


@pytest.mark.e2e
def test_e2e_full_pipeline():
    """Download -> sample -> classify -> dashboard on a tiny corpus."""
    from giftcards import config, dashboard, download, sample

    download.download_raw()
    reviews = download.load_reviews()[:200]
    sampled = sample.stratified_sample(reviews, size=20, seed=42)
    client = classify.get_client()
    results = classify.classify_batch(sampled, client, max_reviews=20)
    assert results, "no results produced"
    as_jsonl = classify.results_to_jsonl(results, config.PROCESSED_DIR / "_e2e.jsonl")
    out = dashboard.build_dashboard(results, config.OUTPUT_DIR / "_e2e_dashboard.html")
    assert as_jsonl.exists()
    assert out.exists()
    assert "Amazon Gift Card" in out.read_text(encoding="utf-8")
