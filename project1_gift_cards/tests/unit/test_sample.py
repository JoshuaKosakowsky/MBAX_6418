"""UNIT tests for stratified sampling. Fast, no network."""
import pytest

from giftcards.sample import split_train_test, stratified_sample

pytestmark = pytest.mark.unit


def _reviews(n, rating):
    return [{"rating": float(rating)} for _ in range(n)]


def test_stratified_smaller_than_total_returns_requested_size():
    reviews = _reviews(100, 5.0) + _reviews(100, 1.0)
    out = stratified_sample(reviews, size=40, seed=7)
    assert len(out) == 40
    # Both ratings must be represented.
    ratings = {r["rating"] for r in out}
    assert ratings == {1.0, 5.0}


def test_stratified_is_reproducible_with_seed():
    reviews = _reviews(150, 4.0) + _reviews(50, 2.0) + _reviews(50, 3.0)
    a = stratified_sample(reviews, size=60, seed=1)
    b = stratified_sample(reviews, size=60, seed=1)
    assert [r["rating"] for r in a] == [r["rating"] for r in b]


def test_full_when_size_none():
    reviews = _reviews(10, 5.0)
    assert len(stratified_sample(reviews, size=None)) == 10


def test_no_sample_larger_than_corpus():
    reviews = _reviews(5, 5.0)
    out = stratified_sample(reviews, size=50, seed=3)
    assert len(out) == 5


def test_split_is_partition():
    reviews = _reviews(100, 5.0)
    train, test = split_train_test(reviews, test_frac=0.2, seed=5)
    assert len(train) + len(test) == 100
    assert len(test) == 20
