# Repository Guidelines

## Project Structure & Module Organization
- Keep core experiment code under `src/`, grouped by agent (`src/agents/<agent_name>.py`) and shared utilities (`src/common/`).
- Place experiment configurations in `configs/` (YAML/JSON) and small, committed sample datasets in `assets/`. Large or generated artifacts belong in `data/` and should be gitignored.
- Mirror code layout in `tests/` (e.g., `tests/agents/test_<agent_name>.py`) so coverage maps cleanly to modules.
- Put developer helpers in `scripts/` and document them briefly in `README.md` or script docstrings.

## Build, Test, and Development Commands
- Create a virtual environment for local work: `python -m venv .venv && source .venv/bin/activate`.
- Install dependencies with lockstep reproducibility: `pip install -r requirements.txt` (or `pip install -e .[dev]` if a package is defined).
- Run the full test suite: `pytest tests`.
- Static checks before pushing: `ruff check src tests` and `black --check src tests` (use `black src tests` to auto-format).
- For quick experiment runs, prefer a single entry point such as `python -m src.main --config configs/example.yaml`; keep example configs runnable.

## Coding Style & Naming Conventions
- Python preferred: follow PEP 8, 4-space indentation, and type hints on public functions. Keep functions focused and under ~50 lines when reasonable.
- Names: modules and files are `snake_case`; classes are `PascalCase`; constants are `UPPER_SNAKE_CASE`.
- Keep configuration keys lower_snake_case and documented in example config files.
- Commit formatted code only; avoid mixing formatting-only changes with logic changes.

## Testing Guidelines
- Use `pytest` with tests colocated in `tests/` mirroring the `src/` tree; name files `test_<module>.py` and tests `test_<behavior>()`.
- Prefer small, deterministic fixtures; avoid network-dependent tests. Use factories or fakes for agent inputs/outputs.
- Target meaningful coverage on new code (logic branches, edge cases, error handling). If you skip a test, justify with a clear `@pytest.mark.skip` reason.

## Commit & Pull Request Guidelines
- Write imperative, present-tense commit messages; Conventional Commits prefixes (`feat:`, `fix:`, `chore:`, `docs:`) are encouraged for clarity.
- Keep commits scoped and reviewable: one logical change per commit when possible.
- Pull requests should include: a short summary, linked issues/tickets, testing notes (`pytest`/lint results), and screenshots or logs when altering behavior.
- Describe experiment intent and outcomes when adding new agents or configs so others can reproduce results.
