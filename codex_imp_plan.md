# Implementation Plan

## Goals
- Stand up a runnable multi-agent CLI demo aligned with README.
- Provide reproducible configs, logging, and minimal tests to validate the loop.

## Phases & Tasks
1) **Scaffold baseline layout**
   - Create `src/agents/` with sample agent personas and shared prompt/template helpers in `src/common/`.
   - Add `src/main.py` entry point (argparse for `--config`, optional `--max-rounds`, `--output-dir`).
   - Ensure `__init__.py` files for module imports.

2) **Config and sample data**
   - Add `configs/example.yaml` defining 2–3 analyst profiles, model name, max rounds, convergence threshold, and logging paths.
   - Include small sample prompt snippets or fixtures in `assets/` if needed by the config.

3) **Agent loop and orchestration**
   - Implement a turn-based discussion loop: load config, instantiate agents, iterate rounds, collect messages, stop on convergence/max rounds.
   - Add judge/aggregator step to produce final recommendation and confidence.
   - Emit structured run artifacts under `runs/<timestamp>/` (config copy, transcript, summary JSON/Markdown).
   - Use LiteLLM to manage APIs.

4) **Tooling and quality gates**
   - Add `requirements.txt` (runtime + dev: `pytest`, `ruff`, `black`) and optional `pyproject.toml` for tool config.
   - Wire `ruff check src tests` and `black src tests` targets (Makefile or simple scripts).
   - Add type hints to public functions; keep functions small and focused.

5) **Testing**
   - Create smoke test in `tests/test_main.py` loading `configs/example.yaml` with stubbed LLMs/fakes.
   - Add unit tests for convergence logic and aggregator output shape.
   - Ensure tests avoid network calls; use fixtures/fakes for model responses.

6) **Docs and handoff**
   - Update `README.md` with actual run command, flags, and sample output path.
   - Keep `AGENTS.md` aligned with conventions and tooling as implemented.
