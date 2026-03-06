# Contributing to SpecDrift

Thanks for contributing — this project is intentionally designed to be friendly to PMs and engineer-PMs as well as core engineers.

## Local setup

### Prereqs

- Python **3.11+**
- Node **20+** (only required if you work on `dashboard/`)

### Install (engine)

```bash
git clone https://github.com/interstellarswapnil-eng/specdrift.git
cd specdrift

python -m venv .venv
source .venv/bin/activate

pip install -U pip
pip install -e ".[dev,engine]"
```

### Run tests

Locally:

```bash
pytest -v tests/
```

Via GitHub Actions:
- Push to a branch / open a PR.
- The **Tests** workflow runs automatically on changes to `specdrift/**`, `tests/**`, and `pyproject.toml`.

## Running the dashboard locally

```bash
cd dashboard
npm install
npm run dev
```

(You can generate a JSON report and drop it into `dashboard/public/drift-report.json`.)

## Submitting PRs

1. Create a feature branch
2. Keep PRs small and focused
3. Add/adjust tests when behaviour changes
4. Ensure CI is green

## Coding conventions

- **Keep dependencies minimal** (stdlib first; add libs only when it’s clearly worth it)
- **Typed Python** where practical (simple type hints help contributors)
- Prefer **pure functions** for parsing/detection logic (easier to test)
- Avoid network calls in unit tests — mock boundary functions instead
- CLI UX: clear error messages; never crash on expected user mistakes

## Reporting bugs / feature requests

- Open an issue with:
  - expected vs actual behaviour
  - repro steps
  - relevant logs / screenshots
  - `specdrift.yaml` (redact secrets)
