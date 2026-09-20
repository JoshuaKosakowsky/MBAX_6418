# Amazon "Gift Cards" Review — Sentiment & Emotion Classifier

Classifies Amazon 2023 *Gift Cards* reviews into **positive / neutral / negative**
and detects the **primary emotion** (six Ekman emotions + neutral), using an
**OpenAI-compatible model endpoint**. The model sees **text only**; star ratings
are preserved as a reference for downstream outlier analysis.

```
download → sample → classify → dashboard
```

## Quick start

```bash
# 1. Environment (each teammate uses their own endpoint)
cp .env.example .env        # fill in OPENAI_BASE_URL, OPENAI_API_KEY, OPENAI_MODEL

# 2. Install deps (uv is the supported tool; see note below)
uv venv && uv pip install -r requirements.txt

# 3. Pull the corpus and build a stratified sample
uv run python main.py download
uv run python main.py sample --size 3000

# 4. Classify the sample
uv run python main.py classify

# 5. Build the dashboard
uv run python main.py dashboard            # -> output/dashboard.html
open output/dashboard.html
```

Use `--full` on `sample` and `--limit N` on `classify` to scale up to the whole
152,410-review corpus as budget allows.

## Commands

| Command | Purpose |
|---|---|
| `download` | Fetch `Gift_Cards.jsonl.gz` (12.29 MB / 152,410 reviews) into `data/raw/` |
| `sample` | Stratify by star rating (default 3,000; `--full` for all) |
| `classify` | Concurrent LLM classification; writes JSONL + CSV to `data/processed/` |
| `smoke` | **Cheap-model** smoke test of end-to-end wiring (AGENTS.md: cheap first) |
| `dashboard` | Render `output/dashboard.html` (single-file, no server, embedded results) |

## Testing (AGENTS.md: Unit → Smoke → End-to-End)

```bash
uv run pytest -m unit             # fast, offline (basis of CI)
uv run pytest -m smoke            # cheap model, requires .env
uv run pytest -m e2e              # full pipeline, requires .env
uv run pytest                     # everything
```

- **Unit** — JSON parsing, sampling, the classify call path (mocked client). No network.
- **Smoke** — cheapest configured model checks wiring end-to-end quickly.
- **End-to-end** — download → sample → classify → dashboard on a small corpus.

## Data notes & outliers

The **star rating is never sent to the model**; sentiment is judged from text.
Ratings 1–2/3/4–5 map to negative/neutral/positive only as a *reference* for
comparing model output against the stars — outlier analysis ("went gift-worthy
positive text under a 2★"? sarcasm under 5★?) is a planned later step built on
these stored, independent signals.

## Workflow & conventions

See `../AGENTS.md` (repo root): Conventional Commits, issue–branch–PR flow,
Bugzilla-style bug reports, and the Unit→Smoke→E2E testing strategy with
cheaper models prioritized for smoke tests.

## Environment note (uv)

This repo uses **uv** for environment management. Deliberately: virtualenv
interpreters created by `python -m venv` are currently refused by the local
Hermes tooling guard, so all commands run through `uv run python` / `uv pip install`.
