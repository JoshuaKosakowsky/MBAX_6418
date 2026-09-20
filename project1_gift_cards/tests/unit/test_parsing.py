"""UNIT tests for JSON parsing helpers. Fast, no network."""
import pytest

from giftcards.parsing import extract_json_object
from giftcards.prompts import build_user_message, parse_classification

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
    def test_valid(self):
        out = parse_classification(
            '{"sentiment":"positive","primary_emotion":"joy",'
            '"sentiment_confidence":0.92,"emotion_confidence":0.8,"evidence":"always good"}'
        )
        assert out["sentiment"] == "positive"
        assert out["primary_emotion"] == "joy"
        assert out["sentiment_confidence"] == 0.92

    def test_rejects_bad_sentiment(self):
        with pytest.raises(ValueError):
            parse_classification('{"sentiment":"mega","primary_emotion":"joy"}')

    def test_rejects_bad_emotion(self):
        with pytest.raises(ValueError):
            parse_classification('{"sentiment":"positive","primary_emotion":"euphoria"}')

    def test_confidence_clamped(self):
        out = parse_classification('{"sentiment":"neutral","primary_emotion":"neutral","sentiment_confidence":1.7}')
        assert out["sentiment_confidence"] == 1.0


class TestPrompt:
    def test_user_message_contains_review_text(self):
        msg = build_user_message({"title": "Hi", "text": "Hello world"})
        assert "Hi" in msg and "Hello world" in msg

    def test_messages_have_system_and_user(self):
        from giftcards.prompts import build_messages

        msgs = build_messages({"title": "Hi", "text": "Hello"})
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"
