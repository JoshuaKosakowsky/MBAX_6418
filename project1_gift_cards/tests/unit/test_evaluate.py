"""UNIT tests for evaluation/scoring. Fast, no network."""
import pytest

from giftcards import evaluate

pytestmark = pytest.mark.unit


class TestRatingLabel:
    def test_three_class_threshold(self):
        assert evaluate.rating_score_label(5.0) == "POSITIVE"
        assert evaluate.rating_score_label(4.0) == "POSITIVE"
        assert evaluate.rating_score_label(3.0) == "NEUTRAL"
        assert evaluate.rating_score_label(2.0) == "NEGATIVE"
        assert evaluate.rating_score_label(1.0) == "NEGATIVE"


class TestEvalBatch:
    def test_balances_three_classes(self):
        reviews = ([{"rating": 5.0}] * 30 + [{"rating": 4.0}] * 20 +
                   [{"rating": 3.0}] * 50 + [{"rating": 2.0}] * 15 +
                   [{"rating": 1.0}] * 35)
        batch = evaluate.build_eval_batch(reviews, size=90, seed=1)
        from collections import Counter
        comp = Counter(evaluate.rating_score_label(r["rating"]) for r in batch)
        assert len(batch) == 90
        assert comp["POSITIVE"] == 30
        assert comp["NEUTRAL"] == 30
        assert comp["NEGATIVE"] == 30

    def test_never_exceeds_available(self):
        reviews = [{"rating": 5.0} for _ in range(3)]
        batch = evaluate.build_eval_batch(reviews, size=100, seed=1)
        assert len(batch) == 3

    def test_reproducible(self):
        reviews = [{"rating": float(r)} for r in [1, 2, 3, 4, 5] * 12]
        a = evaluate.build_eval_batch(reviews, size=30, seed=7)
        b = evaluate.build_eval_batch(reviews, size=30, seed=7)
        assert [r["rating"] for r in a] == [r["rating"] for r in b]


class TestScore:
    def test_correct_confusion_and_balanced(self):
        truth = ["NEGATIVE", "NEGATIVE", "NEUTRAL", "NEUTRAL", "POSITIVE", "POSITIVE"]
        pred = ["NEGATIVE", "POSITIVE", "NEUTRAL", "NEUTRAL", "POSITIVE", "POSITIVE"]  # 1 miss
        res = evaluate.score(zip(truth, pred))
        assert res.overall_accuracy == pytest.approx(5 / 6, abs=0.001)
        # recalls: NEGATIVE 1/2, NEUTRAL 2/2, POSITIVE 2/2 -> mean = (0.5+1+1)/3
        assert res.balanced_accuracy == pytest.approx((0.5 + 1 + 1) / 3, abs=0.01)
        assert res.confusion[("NEGATIVE", "POSITIVE")] == 1
        assert res.per_class["NEUTRAL"].support == 2

    def test_neutral_is_good_class_coverage(self):
        # if NEUTRAL is inferred confidently, it is captured (not swallowed)
        truth = ["NEUTRAL"] * 4 + ["POSITIVE"] * 2
        pred = ["NEUTRAL"] * 3 + ["POSITIVE"] * 3
        res = evaluate.score(zip(truth, pred))  # NEUTRAL recall 3/4
        assert res.per_class["NEUTRAL"].recall == pytest.approx(0.75)

    def test_skew_fools_overall_not_balanced(self):
        truth = ["POSITIVE"] * 50
        pred = ["POSITIVE"] * 50
        res = evaluate.score(zip(truth, pred))
        assert res.overall_accuracy == 1.0
        # NEUTRAL and NEGATIVE never appear -> their recall is 0
        assert res.balanced_accuracy == pytest.approx(1 / 3, abs=0.01)

    def test_disagreements_listed(self):
        rows = [
            {"rating": 5.0, "label": "positive", "confidence": 0.9, "title": "t", "text": "good", "status": "ok"},
            {"rating": 3.0, "label": "positive", "confidence": 0.6, "title": "u", "text": "bad", "status": "ok"},
        ]
        res = evaluate.score([("POSITIVE", "POSITIVE"), ("NEUTRAL", "POSITIVE")])
        evaluate.attach_disagreements(res, rows)
        assert len(res.disagreements) == 1
        assert res.disagreements[0]["truth"] == "NEUTRAL"
        assert res.disagreements[0]["pred"] == "POSITIVE"
