"""Configuration and environment loading for the gift card sentiment project.

All secrets/endpoint settings come from a local `.env` file (gitignored).
Every teammate copies `.env.example` -> `.env` and fills in their own values.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# root = project1_gift_cards/
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# --- Paths ---------------------------------------------------------------
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
SAMPLES_DIR = DATA_DIR / "samples"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = ROOT / "output"
for _d in (RAW_DIR, SAMPLES_DIR, PROCESSED_DIR, OUTPUT_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# --- Data source ----------------------------------------------------------
# The direct McAuley Lab URL (verified working server-side: 12.29 MB / 152,410 reviews).
# Override with GIFT_CARDS_DATA_URL if the source moves.
DEFAULT_DATA_URL = (
    "https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/"
    "raw/review_categories/Gift_Cards.jsonl.gz"
)
DATA_URL = os.environ.get("GIFT_CARDS_DATA_URL", DEFAULT_DATA_URL)
RAW_GZ = RAW_DIR / "Gift_Cards.jsonl.gz"


def require_env(name: str) -> str:
    """Return an env value or raise a clear error pointing at .env setup."""
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(
            f"Environment variable '{name}' is not set. "
            f"Copy {ROOT / '.env.example'} to {ROOT / '.env'} and fill it in."
        )
    return val


def openai_base_url() -> str:
    return require_env("OPENAI_BASE_URL")


def openai_api_key() -> str:
    return require_env("OPENAI_API_KEY")


def default_model() -> str:
    return os.environ.get("OPENAI_MODEL") or "deepseek-chat"


def smoke_model() -> str:
    return os.environ.get("SMOKE_MODEL") or default_model()


def sample_size() -> int:
    try:
        return int(os.environ.get("SAMPLE_SIZE") or "3000")
    except ValueError:
        return 3000


def random_seed() -> int:
    try:
        return int(os.environ.get("RANDOM_SEED") or "42")
    except ValueError:
        return 42


def max_concurrency() -> int:
    try:
        return int(os.environ.get("MAX_CONCURRENCY") or "8")
    except ValueError:
        return 8


def use_responses_format() -> bool:
    return os.environ.get("RESPONSE_FORMAT", "json").lower() != "off"
