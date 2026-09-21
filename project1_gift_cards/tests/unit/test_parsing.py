"""UNIT tests for JSON parsing helpers. Fast, no network."""
import pytest

from giftcards.parsing import extract_json_object
from giftcards.prompts import (
    build_binary_messages,
    build_user_message,
    parse_binary_classification,
    parse_classification,
)

pytestmark = pytest.mark.unit


class TestExtractJson:
    def test_plain_object(self):
        assert extract_json_object('{"a": 1}') == {"a": 1}

    def test_markdown_fence(self):
        raw = "```json\n{\"sentiment\": \"positive\"}\n```"
        assert extract_json_object(raw) == {"sentiment": "positive"}

    def test_fence_with_prose(self):
        raw = 'Sure! Here you go:\n```json\n{"a": 1}\n```\nHope that helps.'
        assert extract_json_object(raw) == {"a": 1}

    def test_trailing_comma_tolerated(self):
        assert extract_json_object('{"a": 1, "b": 2,}') == {"a": 1, "b": 2}

    def test_not_an_object(self):
        with pytest.raises(ValueError):
            extract_json_object("[1, 2, 3]")

    def test_garbage(self):
        with pytest.raises(ValueError):
            extract_json_object("no json here at all")


class TestParseClassification:
    """Three-class label parsing via the canonical parse_classification alias."""

    def test_valid_label(self):
        out = parse_classification(
            '{"label":"POSITIVE","confidence":0.92,"primary_emotion":"joy","reason":"always good"}'
        )
        assert out["label"] == "POSITIVE"
        assert out["primary_emotion"] == "joy"
        assert out["confidence"] == 0.92

    def test_neutral_label(self):
        out = parse_classification(
            '{"label":"NEUTRAL","confidence":0.5,"primary_emotion":"trust","reason":"as expected"}'
        )
        assert out["label"] == "NEUTRAL"

    def test_rejects_unknown_label(self):
        with pytest.raises(ValueError):
            parse_classification('{"label":"MEGA","confidence":0.5,"primary_emotion":"joy"}')

    def test_confidence_clamped(self):
        out = parse_classification(
            '{"label":"NEGATIVE","confidence":1.7,"primary_emotion":"anger"}'
        )
        assert out["confidence"] == 1.0


class TestPrompt:
    def test_user_message_contains_review_text(self):
        msg = build_user_message({"title": "Hi", "text": "Hello world"})
        assert "Hi" in msg and "Hello world" in msg

    def test_messages_have_system_and_user(self):
        from giftcards.prompts import build_messages

        msgs = build_messages({"title": "Hi", "text": "Hello"})
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"


class TestBinaryPrompt:
    def test_messages_take_title_and_text(self):
        msgs = build_binary_messages("Great gift", "Having Amazon money is always good.")
        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"].startswith("You are a sentiment classifier")
        assert "Great gift" in msgs[1]["content"]
        assert "Having Amazon money" in msgs[1]["content"]

    def test_parse_binary_ok(self):
        out = parse_binary_classification(
            '{"label":"POSITIVE","confidence":0.9,"reason":"always good"}'
        )
        assert out["label"] == "POSITIVE"
        assert out["confidence"] == 0.9

    def test_parse_binary_accepts_lowercase(self):
        out = parse_binary_classification('{"label":"negative","confidence":0.8,"reason":"x"}')
        assert out["label"] == "NEGATIVE"

    def test_parse_binary_reads_emotion(self):
        out = parse_binary_classification(
            '{"label":"POSITIVE","confidence":0.9,"primary_emotion":"joy","reason":"x"}'
        )
        assert out["primary_emotion"] == "joy"

    def test_parse_binary_invalid_emotion_becomes_none(self):
        out = parse_binary_classification(
            '{"label":"POSITIVE","confidence":0.9,"primary_emotion":"euphoria","reason":"x"}'
        )
        assert out["primary_emotion"] is None

    def test_parse_binary_rejects_unknown(self):
        with pytest.raises(ValueError):
            parse_binary_classification('{"label":"meh","confidence":0.5,"reason":"x"}')
