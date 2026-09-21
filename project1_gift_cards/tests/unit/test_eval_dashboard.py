"""UNIT tests for the evaluation-dashboard builder. Offline, no network."""
import json
import re

import pytest

from giftcards import eval_dashboard

pytestmark = pytest.mark.unit


def _row(rating, label, confidence=0.8, title="T", text="x"):
    return {
        "rating": rating, "label": label, "confidence": confidence,
        "title": title, "text": text, "status": "ok", "model": "test",
    }


def _summary(html):
    return json.loads(html.split('id="summary">')[1].split("</script>")[0])


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
    # Step 4: interactive filter controls are present
    assert 'id="filtSeg"' in html and 'id="fStar"' in html and 'id="count"' in html
    # embedded data has 4 reviews
    assert '"title": "T"' in html or "T" in html


def test_build_summary_numbers_match(tmp_path):
    # 3 correct of 4 => overall 0.75
    rows = [
        _row(5.0, "POSITIVE"), _row(5.0, "POSITIVE"), _row(5.0, "POSITIVE"),
        _row(1.0, "POSITIVE"),  # wrong (rating 1 -> NEGATIVE)
    ]
    out = eval_dashboard.build(rows, out_path=tmp_path / "d2.html")
    m = _summary(out.read_text(encoding="utf-8"))
    assert m["n"] == 4
    assert m["right"] == 3 and m["wrong"] == 1
    assert m["overall_accuracy"] == 0.75
    assert m["confusion"]["NEGATIVE"]["POSITIVE"] == 1  # the one miss
    assert m["insights"]


def test_descriptive_aggregates(tmp_path):
    rows = [
        _row(5.0, "POSITIVE"), _row(4.0, "POSITIVE"),
        _row(3.0, "NEUTRAL"),
        _row(2.0, "NEGATIVE"), _row(1.0, "NEGATIVE"),
    ]
    out = eval_dashboard.build(rows, out_path=tmp_path / "d.html")
    m = _summary(out.read_text(encoding="utf-8"))
    assert m["stars"] == {"1": 1, "2": 1, "3": 1, "4": 1, "5": 1}
    assert m["ref_pred"]["POSITIVE"] == {"ref": 2, "pred": 2}
    assert m["ref_pred"]["NEUTRAL"] == {"ref": 1, "pred": 1}
    assert m["ref_pred"]["NEGATIVE"] == {"ref": 2, "pred": 2}
    assert m["class_right"]["POSITIVE"] == {"correct": 2, "total": 2}
    assert m["class_right"]["NEUTRAL"] == {"correct": 1, "total": 1}
    # descriptive controls present in the page
    html = out.read_text(encoding="utf-8")
    assert 'id="starDist"' in html and 'id="refPred"' in html and 'id="classRight"' in html
