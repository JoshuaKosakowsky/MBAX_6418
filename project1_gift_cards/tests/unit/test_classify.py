"""UNIT tests for the classification call path using a fake client.

No network: we monkeypatch the underlying OpenAI call so the logic (message
building, response parsing, retry, error marking) is exercised in isolation.
"""
import pytest

from giftcards import classify

pytestmark = pytest.mark.unit


class _FakeResp:
    def __init__(self, content):
        self.choices = [type("C", (), {"message": type("M", (), {"content": content})()})()]


class _FakeClient:
    """Records calls and returns scripted responses / exceptions."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def chat(self):  # pragma: no cover - not used
        pass

    def _call(self):
        item = self.responses[0] if self.responses else None
        if isinstance(item, Exception):
            self.responses.pop(0)
            raise item
        self.responses.pop(0)
        if isinstance(item, str):
            return _FakeResp(item)
        raise TypeError(item)


def test_classify_one_parses_response(monkeypatch):
    client = _FakeClient([])

    def fake_call(client, messages, model):
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        return ('{"sentiment":"negative","primary_emotion":"anger",'
                '"sentiment_confidence":0.9,"emotion_confidence":0.7,"evidence":"useless"}')

    monkeypatch.setattr(classify, "_call_model", fake_call)
    out = classify.classify_one({"title": "Bad", "text": "Terrible.", "rating": 1.0}, client, model="test-model")
    assert out["status"] == "ok"
    assert out["sentiment"] == "negative"
    assert out["primary_emotion"] == "anger"
    assert out["model"] == "test-model"
    # original fields preserved
    assert out["rating"] == 1.0


def test_classify_one_marks_error_after_retries(monkeypatch):
    client = _FakeClient([])

    def boom(client, messages, model):
        raise RuntimeError("timeout")

    monkeypatch.setattr(classify, "_call_model", boom)
    out = classify.classify_one({"text": "x"}, client, retries=1)
    assert out["status"] == "error"
    assert "timeout" in out["error"]


def test_classify_batch_preserves_order(sample_reviews, monkeypatch):
    client = _FakeClient([])

    def fake_call(client, messages, model):
        return ('{"sentiment":"positive","primary_emotion":"joy",'
                '"sentiment_confidence":1.0,"emotion_confidence":1.0,"evidence":"ok"}')

    monkeypatch.setattr(classify, "_call_model", fake_call)
    results = classify.classify_batch(sample_reviews, client, model="m", max_workers=4)
    assert len(results) == len(sample_reviews)
    assert [r["title"] for r in results] == [r["title"] for r in sample_reviews]
    assert all(r["status"] == "ok" for r in results)
