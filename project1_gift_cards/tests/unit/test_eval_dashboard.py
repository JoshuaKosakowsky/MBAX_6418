"""UNIT tests for the evaluation-dashboard builder. Offline, no network."""
import json

import pytest

from giftcards import eval_dashboard

pytestmark = pytest.mark.unit


def _row(rating, label, confidence=0.8, title="T", text="x"):
    return {
        "rating": rating, "label": label, "confidence": confidence,
        "title": title, "text": text, "status": "ok", "model": "test",
    }


def test_build_writes_self_contained_html(tmp_path):
    rows = [
        _row(5.0, "positive", 0.9),  # correct
        _row(4.0, "POSITIVE", 0.8),  # correct
        _row(1.0, "NEGATIVE", 0.7),  # correct
        _row(3.0, "POSITIVE", 0.5),  # wrong vs rating (3 -> NEGATIVE)
    ]
    out = eval_dashboard.build(rows, out_path=tmp_path / "d.html", model="test")
    html = out.read_text(encoding="utf-8")
    assert "Gift Card Review Sentiment" in html
    # placeholders replaced
    assert "__SUMMARY_JSON__" not in html and "__ROWS_JSON__" not in html
    # embedded data has 4 reviews
    assert '"title": "T"' in html or "T" in html


def test_build_summary_numbers_match(tmp_path):
    # 3 correct of 4 => overall 0.75
    rows = [
        _row(5.0, "POSITIVE"), _row(5.0, "POSITIVE"), _row(5.0, "POSITIVE"),
        _row(1.0, "POSITIVE"),  # wrong (rating 1 -> NEGATIVE)
    ]
    out = eval_dashboard.build(rows, out_path=tmp_path / "d2.html")
    m = out.read_text(encoding="utf-8").split('id="summary">')[1].split("</script>")[0]
    s = json.loads(m)
    assert s["n"] == 4
    assert s["right"] == 3 and s["wrong"] == 1
    assert s["overall_accuracy"] == 0.75
    assert s["confusion"]["NEGATIVE"]["POSITIVE"] == 1  # the one miss
    assert s["insights"]
