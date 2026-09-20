"""Prompt builders for the sentiment/emotion classifier.

The model is asked to classify based on the written TEXT ONLY. The star rating
is intentionally NOT an input to the model call: downstream outlier analysis
(star rating vs. detected sentiment) is a later step and must be derived from
the two independently produced signals.
"""

from __future__ import annotations

import json

from .emotions import EKMAN_EMOTIONS, SENTIMENTS

SYSTEM_PROMPT = """You are an expert sentiment analyst for Amazon product reviews.

Classify the sentiment ONLY from the written review text (title + text).
You will NOT be shown a star rating — do not infer one. Judge the words.

Rules:
- sentiment must be one of: {sentiments}
- primary_emotion must be one of: {emotions}
- If the text is factual, brief, or carries no clear feeling (e.g. "Purchased as a gift."),
  choose sentiment "neutral" and primary_emotion "neutral". Do not invent feeling.
- Handle sarcasm, humor, and contradictions by judging the overall intent of the words.
- Return ONLY a valid JSON object — no markdown, no prose — with exactly these keys:
  "sentiment", "primary_emotion", "sentiment_confidence", "emotion_confidence", "evidence"
- sentiment_confidence / emotion_confidence are floats in [0,1] expressing your certainty.
- evidence: a short quoted phrase (12 words or fewer) from the text that best supports
  your sentiment call.
""".format(sentiments=SENTIMENTS, emotions=EKMAN_EMOTIONS)


def build_user_message(review: dict) -> str:
    """Compose the user turn for a single review record."""
    title = (review.get("title") or "").strip()
    text = (review.get("text") or "").strip()
    combined = f"{title}\n\n{text}".strip()
    return (
        "Review:\n"
        "------\n"
        f"{combined}\n\n"
        "Return your classification as a JSON object with keys "
        "sentiment, primary_emotion, sentiment_confidence, "
        "emotion_confidence, evidence."
    )


def build_messages(review: dict) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_message(review)},
    ]


def parse_classification(raw: str) -> dict:
    """Robustly parse a classification JSON out of a model response.

    Tolerates stray text, markdown code fences, and minor issues. Raises
    ValueError on failure so callers can retry/mark the record.
    """
    from .parsing import extract_json_object

    obj = extract_json_object(raw)
    if not isinstance(obj, dict):
        raise ValueError("model response did not contain a JSON object")

    sentiment = str(obj.get("sentiment", "")).strip().lower()
    emotion = str(obj.get("primary_emotion", "")).strip().lower()

    if sentiment not in SENTIMENTS:
        raise ValueError(f"unknown sentiment value: {sentiment!r}")
    if emotion not in EKMAN_EMOTIONS:
        raise ValueError(f"unknown emotion value: {emotion!r}")

    return {
        "sentiment": sentiment,
        "primary_emotion": emotion,
        "sentiment_confidence": _float(obj.get("sentiment_confidence")),
        "emotion_confidence": _float(obj.get("emotion_confidence")),
        "evidence": str(obj.get("evidence", "")).strip()[:120],
    }


def _float(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return round(min(max(f, 0.0), 1.0), 3)
