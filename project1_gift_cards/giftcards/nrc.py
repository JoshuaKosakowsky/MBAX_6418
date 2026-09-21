"""NRC word-list emotion scoring (no model calls).

Uses the public **NRC Word-Emotion Association Lexicon** (v0.92; Mohammad &
Turney 2013, *Computational Intelligence* 29(3)). Bundled under
``giftcards/assets/nrc_emotion_lexicon.txt``; per the license notice it is for
research purposes — this is a course project.

The lexicon links English words to eight basic emotions: anger, anticipation,
disgust, fear, joy, sadness, surprise, and trust. The word-list method scores
each review's tokens against the lexicon, sums the association counts per
emotion, and takes the highest-scoring emotion as the derived primary emotion.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

# The eight basic emotions covered by the NRC lexicon.
NRC_EMOTIONS = [
    "anger", "anticipation", "disgust", "fear", "joy",
    "sadness", "surprise", "trust",
]

_ASSETS = Path(__file__).resolve().parent / "assets" / "nrc_emotion_lexicon.txt"
_TOKEN_RE = re.compile(r"[A-Za-z']+")


def load_lexicon(path: Path | None = None) -> dict[str, set[str]]:
    """Return {word_lower: {emotion, ...}} for words associated (flag == 1)
    with any of the eight NRC emotions. Skips header/license lines."""
    lex: dict[str, set[str]] = {}
    src = path or _ASSETS
    with src.open(encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) != 3:
                continue
            word, emotion, flag = parts
            if flag != "1" or emotion not in NRC_EMOTIONS:
                continue
            lex.setdefault(word.lower(), set()).add(emotion)
    return lex


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


def score_emotions(text: str, lexicon: dict[str, set[str]] | None = None) -> Counter:
    """Sum NRC association counts per emotion across the review's tokens.

    A word may associate with several emotions; each association contributes
    one point to that emotion. Returns a Counter over NRC_EMOTIONS."""
    lex = lexicon if lexicon is not None else load_lexicon()
    scores: Counter = Counter({e: 0 for e in NRC_EMOTIONS})
    for word in tokenize(text):
        for emo in lex.get(word, ()):
            scores[emo] += 1
    return scores


def primary_emotion(text: str, lexicon: dict[str, set[str]] | None = None) -> str | None:
    """Highest-scoring NRC emotion for the text, or None if nothing matches.

    Ties are broken deterministically by first position in ``NRC_EMOTIONS``
    order, so repeated calls give the same answer."""
    scores = score_emotions(text, lexicon)
    best_count = max(scores.values(), default=0)
    if best_count == 0:
        return None
    for emo in NRC_EMOTIONS:
        if scores[emo] == best_count:
            return emo
    return None


def compare(
    llm: list[str | None], nrc_list: list[str | None]
) -> dict:
    """Compare two primary-emotion signals (LLM vs NRC word list).

    Agreement is computed only over reviews where BOTH signals are present.
    Returns counts, agreement rate, per-signal distributions, and the list of
    diverging (llm, nrc) emotion pairs."""
    from collections import Counter

    valid = [(l, n) for l, n in zip(llm, nrc_list) if l and n]
    agree = sum(1 for l, n in valid if l == n)
    return {
        "n": len(valid),
        "agree": agree,
        "disagree": len(valid) - agree,
        "agreement_rate": (round(agree / len(valid), 4) if valid else 0.0),
        "llm_distribution": dict(sorted(Counter(l for l, _ in valid).items(), key=lambda kv: -kv[1])),
        "nrc_distribution": dict(sorted(Counter(n for _, n in valid).items(), key=lambda kv: -kv[1])),
        "divergences": [(l, n) for l, n in valid if l != n],
    }
