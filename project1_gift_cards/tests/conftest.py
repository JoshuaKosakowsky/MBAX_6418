"""Shared pytest fixtures. Ensures the project root is importable."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def sample_reviews():
    return [
        {"title": "Great gift", "text": "Having Amazon money is always good.", "rating": 5.0},
        {"title": "Meh", "text": "The card arrived but the design is boring.", "rating": 3.0},
        {"title": "Terrible", "text": "Never received my balance, support is useless.", "rating": 1.0},
        {"title": "Nice", "text": "Easy to redeem and instantly added to my account.", "rating": 4.0},
        {"title": "Avoid", "text": "Took a week to arrive and the code never worked.", "rating": 2.0},
    ]
