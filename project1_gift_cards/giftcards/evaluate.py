"""Score the classifier against a rating-derived reference label.

The reference ("correct answer") is derived from the STAR RATING only and is used
solely for CHECKING afterwards — the model never sees the rating. Three classes:
    rating in {4, 5} -> POSITIVE
    rating == 3      -> NEUTRAL
    rating in {1, 2} -> NEGATIVE

The corpus is heavily skewed toward 4-5 stars, so a naive accuracy on a random
batch would look flattering most classes invisible. To keep that lopsidedness
from fooling us we build a balanced batch (~equal per class, fixed seed) so every
class is measured, and we report balanced accuracy (mean per-class recall).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Iterable

CLASSES = ["NEGATIVE", "NEUTRAL", "POSITIVE"]


def rating_score_label(rating) -> str:
    """Reference label derived from the star rating (three classes)."""
    r = float(rating or 0)
    if r >= 4:
        return "POSITIVE"
    if r == 3:
        return "NEUTRAL"
    return "NEGATIVE"


def build_eval_batch(reviews: Iterable[dict], size: int, seed: int | None = None) -> list[dict]:
    """A balanced eval batch (~equal per class) so every class is measured despite
    the corpus skew. Fixed seed -> reproducible set every time. Never overflows ``size``.
    """
    reviews = list(reviews)
    n = len(reviews)
    if size is None or size >= n:
        return reviews[:]
    idx = list(range(n))
    rng = random.Random(seed)
    buckets = {
        c: [i for i in idx if rating_score_label(reviews[i].get("rating")) == c]
        for c in CLASSES
    }
    per = max(1, size // len(CLASSES))
    chosen = []
    for c in CLASSES:
        chosen.extend(rng.sample(buckets[c], min(per, len(buckets[c]))))
    chosen_set = set(chosen)
    rest = [i for i in idx if i not in chosen_set]
    rng.shuffle(rest)
    chosen.extend(rest[: max(0, size - len(chosen))])
    rng.shuffle(chosen)
    return [reviews[i] for i in chosen[:size]]


@dataclass
class ClassMetrics:
    precision: float
    recall: float
    f1: float
    support: int


@dataclass
class ScoreResult:
    n: int
    overall_accuracy: float
    balanced_accuracy: float
    per_class: dict[str, ClassMetrics] = field(default_factory=dict)
    confusion: dict[tuple[str, str], int] = field(default_factory=dict)
    disagreements: list[dict] = field(default_factory=list)


def score(pairs: Iterable[tuple[str, str]]) -> ScoreResult:
    """Score a list of (reference_label, predicted_label) pairs."""
    pairs = list(pairs)
    n = len(pairs)
    correct = sum(t == p for t, p in pairs)
    conf: dict[tuple[str, str], int] = {}
    truth_counts = {c: 0 for c in CLASSES}
    pred_counts = {c: 0 for c in CLASSES}

    # Per-class TP/FP/FN
    tp = {c: 0 for c in CLASSES}
    fn = {c: 0 for c in CLASSES}
    fp = {c: 0 for c in CLASSES}

    for truth, pred in pairs:
        truth_counts[truth] = truth_counts.get(truth, 0) + 1
        pred_counts[pred] = pred_counts.get(pred, 0) + 1
        conf[(truth, pred)] = conf.get((truth, pred), 0) + 1
        for c in CLASSES:
            if truth == c and pred == c:
                tp[c] += 1
            elif truth == c:
                fn[c] += 1
            elif pred == c:
                fp[c] += 1

    per_class: dict[str, ClassMetrics] = {}
    recalls: list[float] = []
    for c in CLASSES:
        precision = _safe_div(tp[c], tp[c] + fp[c])
        recall = _safe_div(tp[c], tp[c] + fn[c])
        f1 = _safe_div(2 * precision * recall, precision + recall)
        per_class[c] = ClassMetrics(precision, recall, f1, truth_counts.get(c, 0))
        recalls.append(recall)

    balanced_acc = (sum(recalls) / len(recalls)) if recalls else 0.0
    overall = _safe_div(correct, n)

    return ScoreResult(
        n=n,
        overall_accuracy=round(overall, 4),
        balanced_accuracy=round(balanced_acc, 4),
        per_class=per_class,
        confusion=conf,
        disagreements=[],
    )


def attach_disagreements(result: ScoreResult, rows: Iterable[dict]) -> None:
    """Populate result.disagreements with human-readable wrong rows.

    Each row carries the review fields PLUS a 'pred_label'. The reference is
    derived from the row's rating here (not the model).
    """
    result.disagreements = []
    for r in rows:
        if r.get("status") == "error":
            continue
        truth = rating_score_label(r.get("rating"))
        pred = (r.get("label") or "").upper()
        if pred in CLASSES and pred != truth:
            result.disagreements.append(
                {
                    "rating": r.get("rating"),
                    "truth": truth,
                    "pred": pred,
                    "confidence": r.get("confidence"),
                    "title": r.get("title") or "",
                    "text": (r.get("text") or "").strip()[:220],
                }
            )
    result.disagreements.sort(key=lambda d: d["rating"])


def _safe_div(a: float, b: float) -> float:
    return round(a / b, 3) if b else 0.0


def pretty_report(res: ScoreResult) -> str:
    """Human-readable summary of a ScoreResult."""
    lines = []
    lines.append(f"Evaluated {res.n} reviews (reference = rating-derived, model never saw rating)")
    lines.append(f"Overall accuracy      : {res.overall_accuracy:.1%}")
    lines.append(f"Balanced accuracy     : {res.balanced_accuracy:.1%}  (mean per-class recall; "
                 f"unbiases the rating skew)")
    lines.append("")
    lines.append(f"{'':<9}{'prec':>7}{'recall':>8}{'f1':>7}{'supp':>6}")
    for c in CLASSES:
        m = res.per_class[c]
        lines.append(
            f"{c:<9}{m.precision:>7.2f}{m.recall:>8.2f}{m.f1:>7.2f}{m.support:>6}"
        )
    lines.append("")
    lines.append("Confusion (truth rows x pred cols):")
    lines.append(f"{'':>10}" + "".join(f"{c:>11}" for c in CLASSES))
    for t in CLASSES:
        row = "".join(f"{(res.confusion.get((t,p),0)):>11}" for p in CLASSES)
        lines.append(f"{t:<10}{row}")
    lines.append("")
    lines.append(f"Disagreements: {len(res.disagreements)}")
    return "\n".join(lines)
