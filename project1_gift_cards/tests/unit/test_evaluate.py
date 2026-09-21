"""UNIT tests for evaluation/scoring. Fast, no network."""
import pytest

from giftcards import evaluate

pytestmark = pytest.mark.unit


class TestRatingLabel:
    def test_threshold(self):
        assert evaluate.rating_score_label(5.0) == "POSITIVE"
        assert evaluate.rating_score_label(4.0) == "POSITIVE"
        assert evaluate.rating_score_label(3.0) == "NEGATIVE"
        assert evaluate.rating_score_label(2.0) == "NEGATIVE"
        assert evaluate.rating_score_label(1.0) == "NEGATIVE"


class TestEvalBatch:
    def test_balances_positive_and_negative(self):
        reviews = [{"rating": 5.0} for _ in range(80)] + [{"rating": 1.0} for _ in range(80)]
        batch = evaluate.build_eval_batch(reviews, size=100, seed=1)
        pos = sum(1 for r in batch if r["rating"] >= 4)
        neg = sum(1 for r in batch if r["rating"] < 4)
        assert len(batch) == 100
        assert pos == 50 and neg == 50

    def test_never_exceeds_available(self):
        reviews = [{"rating": 5.0} for _ in range(3)]
        batch = evaluate.build_eval_batch(reviews, size=100, seed=1)
        assert len(batch) == 3

    def test_reproducible(self):
        reviews = [{"rating": float(r)} for r in [1, 2, 3, 4, 5, 1, 2, 3, 4, 5] * 10]
        a = evaluate.build_eval_batch(reviews, size=20, seed=42)
        b = evaluate.build_eval_batch(reviews, size=20, seed=42)
        assert [r["rating"] for r in a] == [r["rating"] for r in b]


class TestScore:
    def test_balanced_matrix(self):
        truth = ["POSITIVE", "POSITIVE", "POSITIVE", "POSITIVE",
                 "NEGATIVE", "NEGATIVE", "NEGATIVE", "NEGATIVE"]
        pred = ["POSITIVE", "POSITIVE", "POSITIVE", "NEGATIVE",
                "NEGATIVE", "NEGATIVE", "NEGATIVE", "POSITIVE"]
        res = evaluate.score(zip(truth, pred))
        assert res.overall_accuracy == 0.75
        assert res.balanced_accuracy == 0.75
        assert res.confusion[("POSITIVE", "POSITIVE")] == 3
        assert res.confusion[("NEGATIVE", "NEGATIVE")] == 3
        assert res.confusion[("POSITIVE", "NEGATIVE")] == 1
        assert res.confusion[("NEGATIVE", "POSITIVE")] == 1

    def test_skew_fools_overall_but_not_balanced(self):
        # All 5-star (positive) reviews, model predicts all positive: high accuracy,
        # but the model never actually separates negatives -> balanced accuracy drops.
        truth = ["POSITIVE"] * 50 + ["NEGATIVE"] * 0  # pure positive set
        pred = ["POSITIVE"] * 50
        res = evaluate.score(zip(truth, pred))
        assert res.overall_accuracy == 1.0
        # NEGATIVE never appeared, so its precision is 0 -> balanced accuracy ~0.5
        assert res.balanced_accuracy == 0.5
        assert res.per_class["NEGATIVE"].support == 0

    def test_disagreements_listed(self):
        rows = [
            {"rating": 5.0, "label": "positive", "confidence": 0.9, "title": "t", "text": "good", "status": "ok"},
            {"rating": 1.0, "label": "positive", "confidence": 0.6, "title": "u", "text": "bad", "status": "ok"},
        ]
        res = evaluate.score([("POSITIVE", "POSITIVE"), ("NEGATIVE", "POSITIVE")])
        evaluate.attach_disagreements(res, rows)
        assert len(res.disagreements) == 1
        assert res.disagreements[0]["truth"] == "NEGATIVE"
        assert res.disagreements[0]["pred"] == "POSITIVE"
