# Contributing to redink

redink is opinionated by design. Contributions are welcome but must respect the constraints below.

## The three constraints (non-negotiable)

1. **Stdlib-only at runtime.** No `httpx`, `pydantic`, `rich`, `click`. `argparse` + `json` + `urllib` + ANSI escapes is the toolbox. See [ADR-001](docs/decisions/ADR-001-stdlib-only.md).
2. **The install command stays one shell line forever.** Every PR is checked against this.
3. **Opinion before features.** redink has a point of view. Features that dilute the opinion don't ship.

## Setup

```bash
git clone git@github.com:danishvirani/redink.git ~/code/redink
cd ~/code/redink
./install.sh
pip install -e ".[dev]"
pytest tests/ -v
```

## Workflow

1. Branch from `main`. Naming: `feat-short-desc`, `fix-short-desc`, `docs-short-desc`.
2. Open the PR as a draft. Mark Ready when self-reviewed and CI is green.
3. Add tests for new behavior. The scoring rules especially need fixture-driven tests.
4. CI must pass on Python 3.10 / 3.11 / 3.12 across Ubuntu + macOS.

## What we won't merge

- New runtime dependencies (even small ones)
- Framework-y abstractions (decorators-as-API, metaclasses, plugin systems)
- Per-user config files outside `~/.config/redink/`
- Features that require a Node toolchain
- Scoring rules without an attached opinion. Every rule needs a one-paragraph rationale in `docs/rules/`.
- Marketing-shaped commit messages ("revolutionary", "AI-powered", etc.)

## Code style

- `argparse`, not `click`
- `json.loads` + `dataclasses`, not `pydantic`
- `print` + ANSI escape constants, not `rich`
- Module-level functions before classes. Classes only when state is real.
- Match the existing patterns in `src/redink/cli.py`.

## Reporting bugs

Open an issue with: redink version (`redink version`), Python version, the command you ran, the output you got, the output you expected.
