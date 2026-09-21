"""UNIT tests for the NRC word-list emotion scorer (offline)."""
import pytest

from giftcards import nrc

pytestmark = pytest.mark.unit


class TestLexiconLoad:
    def test_known_words_loaded(self):
        lex = nrc.load_lexicon()
        assert "good" in lex
        assert "joy" in lex["good"]
        assert "terrible" in lex
        assert "anger" in lex["terrible"]

    def test_covers_eight_emotions(self):
        lex = nrc.load_lexicon()
        found = set()
        for emos in lex.values():
            found |= emos
        assert nrc.NRC_EMOTIONS == sorted(found, key=nrc.NRC_EMOTIONS.index)


class TestScoring:
    def test_primary_joy(self):
        assert nrc.primary_emotion("I just love this, it makes me so happy") == "joy"

    def test_primary_negative_cluster(self):
        # terrible/awful map to anger/disgust/fear/sadness; expect one of them
        assert nrc.primary_emotion("This is a terrible, awful experience") in {
            "anger", "disgust", "fear", "sadness",
        }

    def test_explicit_surprise(self):
        assert nrc.primary_emotion("I am surprised how great this is") == "surprise"

    def test_no_match_returns_none(self):
        assert nrc.primary_emotion("zzqzqx") is None

    def test_scores_sum_individual_emotions(self):
        scores = nrc.score_emotions("good")
        assert scores["joy"] >= 1
        assert scores["trust"] >= 1

    def test_tie_is_deterministic(self):
        a = nrc.primary_emotion("trust joy")  # both match; deterministic tie-break
        b = nrc.primary_emotion("trust joy")
        assert a == b


class TestCompare:
    def test_agreement_rate_and_divergences(self):
        llm = ["joy", "joy", "sadness", "anger", "fear", None]
        nro = ["joy", "trust", "sadness", "sadness", "fear", "joy"]
        stats = nrc.compare(llm, nro)
        # valid pairs (both present): joy/joy agree, joy/trust differ,
        # sadness/sadness agree, anger/sadness differ, fear/fear agree => 3/5
        assert stats["n"] == 5
        assert stats["agree"] == 3
        assert stats["agreement_rate"] == pytest.approx(0.6)
        assert len(stats["divergences"]) == 2
        assert ("joy", "trust") in stats["divergences"]
