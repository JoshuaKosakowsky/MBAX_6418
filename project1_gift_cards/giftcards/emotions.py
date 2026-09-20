"""Label taxonomies for the sentiment/emotion classifier.

Emotion set: the six basic (Ekman) emotions plus neutral, per project spec.
"""

SENTIMENTS = ["positive", "neutral", "negative"]

# Six Ekman basic emotions + neutral (primary emotion taxonomy).
EKMAN_EMOTIONS = ["joy", "sadness", "anger", "fear", "surprise", "disgust", "neutral"]

# Visible labels for dashboards/reports.
HUMAN = {
    "positive": "Positive",
    "neutral": "Neutral",
    "negative": "Negative",
    "joy": "Joy",
    "sadness": "Sadness",
    "anger": "Anger",
    "fear": "Fear",
    "surprise": "Surprise",
    "disgust": "Disgust",
    "neutral_emotion": "Neutral",
}
