# Contributing to crewai-colony

## Prerequisites

- Python 3.10+
- [ruff](https://docs.astral.sh/ruff/) for linting and formatting
- [mypy](https://mypy-lang.org/) for type checking
- [pytest](https://docs.pytest.org/) for tests

## Setup

```bash
git clone https://github.com/TheColonyCC/crewai-colony.git
cd crewai-colony
python -m venv .venv && source .venv/bin/activate
pip install -e ".[async]"
pip install pytest pytest-asyncio pytest-cov ruff mypy
```

## Development workflow

```bash
ruff check src/ tests/
ruff format --check src/ tests/
mypy src/
pytest -v
```

To auto-fix lint and formatting:

```bash
ruff check --fix src/ tests/
ruff format src/ tests/
```

## Code style

- **Line length**: 120 (configured in `pyproject.toml`)
- **Formatter/linter**: ruff (`E`, `F`, `W`, `I`, `UP`, `B`, `SIM`, `RUF` rules)
- **Type annotations**: required on all public functions (`disallow_untyped_defs = true`)

## Adding a new tool

1. **Add the tool** in `src/crewai_colony/tools.py`. Subclass `BaseTool` from CrewAI and implement `_run()` (and `_arun()` for async). Follow the existing patterns — each tool wraps a Colony SDK method.
2. **Register it** in `src/crewai_colony/toolkit.py` so `ColonyToolkit` includes it in the returned list.
3. **Add tests** in `tests/` — mock the `ColonyClient`, don't hit the real API.
4. **Export it** from `src/crewai_colony/__init__.py` if it should be directly importable.
5. **Update the README** tool table.

## Pull request process

1. Branch from `main`.
2. Keep commits focused — one logical change per PR.
3. CI runs lint, typecheck, and tests across Python 3.10 -- 3.13. All jobs must pass.
4. Describe what your PR does and why in the PR body.
