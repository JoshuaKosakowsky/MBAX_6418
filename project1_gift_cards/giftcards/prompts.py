"""Prompt builders for the sentiment/emotion classifier.

The model is asked to classify based on the written TEXT ONLY. The star rating
is intentionally NOT an input to the model call: downstream outlier analysis
(star rating vs. detected sentiment) is a later step and must be derived from
the two independently produced signals.
"""

from __future__ import annotations

import json

from .emotions import EKMAN_EMOTIONS, SENTIMENTS

CLASS_LABELS = ["POSITIVE", "NEUTRAL", "NEGATIVE"]

# Canonical three-class sentiment + primary-emotion prompt (Step 6).
# The canonical prompt is build_binary_messages / parse_binary_classification
# (names kept for step continuity); these aliases keep the generic classify path
# consistent so every call site is on the same three-class label set.
SYSTEM_PROMPT = """You are a sentiment classifier for Amazon product reviews.

Given a review's TITLE and TEXT, do two things:
1. Classify the overall sentiment as POSITIVE, NEUTRAL, or NEGATIVE - exactly one.
2. Pick the PRIMARY EMOTION the text expresses, exactly one from this set:
   anger, anticipation, disgust, fear, joy, sadness, surprise, trust.

Decide ONLY from the words written. No star rating is provided; never invent one.

Class semantics:
- POSITIVE: clearly favourable (praise, satisfaction, recommendation).
- NEGATIVE: complaints, frustration, warnings, disappointment.
- NEUTRAL: no clear positive or negative feeling (e.g. "Purchased as a gift.",
  "As expected", "Received it"). Reserve NEUTRAL for genuinely flat/ambivalent
  text; do not downgrade real positives or negatives to it.

Edge-case policy:
- TITLE vs TEXT conflict: trust the TEXT body as the primary signal.
- Sarcasm / irony: classify the literal underlying intent.
- Terse reviews: a single word can decide ("love it" = POSITIVE, "useless" = NEGATIVE).
- Angry outbursts, rants, complaints: NEGATIVE.
- No clear feeling: choose POSITIVE or NEGATIVE only on real evidence, else NEUTRAL.
- Primary emotion: the dominant emotion from the set; even when flat, choose the
  single closest emotion (e.g. "trust"/"anticipation" for mildly positive,
  "fear"/"sadness" for worried complaints).

Respond with ONLY a JSON object - no markdown - with exactly these keys:
{"label": "POSITIVE" or "NEUTRAL" or "NEGATIVE",
 "confidence": <float 0.0-1.0>,
 "primary_emotion": "anger" or "anticipation" or "disgust" or "fear" or "joy" or
                    "sadness" or "surprise" or "trust",
 "reason": "<1-10 words>"}
where reason is a terse justification from the review's words."""


def build_user_message(review: dict) -> str:
    """Compose the user turn for a review record (three-class)."""
    return build_binary_user_message(review.get("title", ""), review.get("text", ""))


def build_messages(review: dict) -> list[dict]:
    return build_binary_messages(review.get("title", ""), review.get("text", ""))


def parse_classification(raw: str) -> dict:
    """Parse a three-class classification response."""
    return parse_binary_classification(raw)


BINARY_LABELS = ["POSITIVE", "NEUTRAL", "NEGATIVE"]
# Canonical three-class prompt (see SYSTEM_PROMPT above). Kept as an alias so the
# binary-named builders/parser and the generic classify path share one definition.
BINARY_SYSTEM_PROMPT = SYSTEM_PROMPT


def build_binary_user_message(title: str, text: str) -> str:
    combined = f"{title}\n\n{text}".strip()
    return (
        "Review:\n"
        "------\n"
        f"{combined}\n\n"
        'Return only a JSON object: {"label":"POSITIVE"|"NEUTRAL"|"NEGATIVE",'
        '"confidence":<0.0-1.0>,"primary_emotion":"<one of anger, anticipation, '
        'disgust, fear, joy, sadness, surprise, trust>","reason":"<short>"}.'
    )


def build_binary_messages(title: str, text: str) -> list[dict]:
    return [
        {"role": "system", "content": BINARY_SYSTEM_PROMPT},
        {"role": "user", "content": build_binary_user_message(title, text)},
    ]


def parse_binary_classification(raw: str) -> dict:
    """Parse a binary-classification JSON response. Raises ValueError on garbage.

    primary_emotion is validated against the NRC emotion set when present;
    if absent/invalid it is set to None rather than failing the sentiment call.
    """
    from .parsing import extract_json_object
    from .nrc import NRC_EMOTIONS

    obj = extract_json_object(raw)
    if not isinstance(obj, dict):
        raise ValueError("model response did not contain a JSON object")

    label = str(obj.get("label", "")).strip().upper()
    if label not in BINARY_LABELS:
        raise ValueError(f"unknown binary label: {label!r}")

    emotion = str(obj.get("primary_emotion", "")).strip().lower()
    if emotion not in NRC_EMOTIONS:
        emotion = None

    return {
        "label": label,
        "confidence": _float(obj.get("confidence")),
        "primary_emotion": emotion,
        "reason": str(obj.get("reason", "")).strip()[:120],
    }


def _float(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return round(min(max(f, 0.0), 1.0), 3)
