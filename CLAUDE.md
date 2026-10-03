# Project context
A small CLI tool that reads `events.csv` (columns: timestamp, level, service, message)
and prints a counted summary grouped by service and log level.
Case: Meridian Phase 1 — services: checkout-service, cart-api, identity-service.
Language: Python 3.11+.

# Conventions
- All source code in `src/`.
- All tests in `tests/`.
- Use `pytest` for tests; `ruff` for linting.
- Type hints on all public functions.
- No production data, no real log files, no secrets.

# Utilities to prefer
- `csv` (stdlib) for parsing — not pandas.
- `argparse` (stdlib) for CLI — not click or typer.
- `collections.Counter` for aggregation.

# Escalation gates
- Do not write to files outside `src/` and `tests/` without asking.
- Do not install new packages without asking.
- Do not run shell commands that touch the network.