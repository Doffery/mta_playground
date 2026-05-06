# mta_playground
Playground for a multi-agent financial analysis system driven by LLMs.

## Overview
Users provide a topic (company name, news item, or market event) and select from pre-defined analyst profiles (e.g., Warren Buffett–style value investor, Peter Lynch–style growth investor). The agents discuss the topic, share perspectives, debate trade-offs, and converge on a concise investment opinion. Outputs include the full conversation trace and a final summary.

## Current UX
- **V1 (CLI):** Run the script, enter a prompt, watch the agent discussion, and receive the conclusion and transcript. Keep prompts short and specific to get focused outputs.
- **V2 (Web UI):** Having an web UI to handle the innput, output in text format.
- **V3 (RAG System):** Have access to search, to open web and financial API.
- **V4 (Podcast):** Support a Notebook LM alike podcast to provide a fun interesting dialogue alike discussion.
- **V5 (Deep Research):** Each investor is supported by a deep research system, that it can do a thorough deep researcha and think, so in discussion, they can talke with evidence.
- **V6 (Daily Pushes):** Every day, this pushes a new podcast for drive listening.

## Repository Layout
- `src/`: core agent logic, orchestrators, and shared utilities (`src/agents/`, `src/common/`).
- `configs/`: runnable experiment configs documenting analyst profiles and model settings.
- `tests/`: mirrors `src/` for `pytest` coverage; name files `test_<module>.py`.
- `assets/`/`data/`: small committed samples in `assets/`; large/generated artifacts in `data/` (gitignored).
- `AGENTS.md`: contributor guidelines (structure, naming, review expectations).

## Getting Started
1) Create a virtual environment: `python -m venv .venv && source .venv/bin/activate`
2) Install dependencies (when defined): `pip install -r requirements.txt` or `pip install -e .[dev]`
3) Run checks (once present): `pytest tests`, `ruff check src tests`, and `black --check src tests`.

## Running the Demo
Run the CLI:

```bash
python -m src.main --config configs/example.yaml --topic "Google's future growth"
```

Run the UX V2 local web UI:

```bash
python -m src.web --config configs/example.yaml --port 8000
```

Then open `http://127.0.0.1:8000`. The web UI uses the configured LiteLLM model and writes outputs to `runs/<timestamp>/`.

Log outputs to `runs/<timestamp>/` and emit a short summary at the end (participants, key points, final stance).

## Architecture Notes
- Backbone: LLMs for reasoning; prompt templates encode each analyst’s persona and risk tolerance.
- Orchestration: turn-based discussion until convergence or a max round count; a judge/aggregator agent produces the final recommendation.
- Safety: flag low-confidence outputs and missing data.

## Roadmap / Next Steps
- Scaffold `src/main.py` with a minimal agent loop and a sample config in `configs/example.yaml`.
- Add fixtures and smoke tests mirroring the sample config.
- Capture experiment metadata (prompt version, model, seed) in run outputs for reproducibility.
