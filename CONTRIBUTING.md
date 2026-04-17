# Contributing to AGNIWATCH

Thanks for contributing to AGNIWATCH.

## Development Setup

1. Clone and enter the repo.
2. Create a virtual environment.
3. Install dependencies.
4. Run tests and app.

```bash
git clone https://github.com/<your-org>/agniwatch.git
cd agniwatch
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python tests/test_emissions.py
python tests/test_indices.py
streamlit run streamlit_app.py
```

## Pull Request Guidelines

1. Keep changes focused.
2. Include tests for logic changes.
3. Update docs when behavior changes.
4. Ensure app starts and tests pass before opening PR.

## Adding a New Region

1. Copy `regions/template.yaml`.
2. Name it as `country_region.yaml`.
3. Fill required fields and valid bounds `[W, S, E, N]`.
4. Add realistic `sub_regions` mapping.
5. Open PR with short evidence note (data source/crop season).

## Code Style

- Use clear function names and type hints where useful.
- Prefer small modules with explicit responsibilities.
- Avoid committing credentials or secrets.

## Reporting Issues

Open a GitHub issue with:
- Steps to reproduce
- Region and date window
- Error message/trace
- Expected vs actual behavior
