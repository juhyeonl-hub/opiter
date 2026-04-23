# Contributing to Opiter

Opiter is in early **pre-alpha** stage. The codebase is small and actively evolving. Please read this before opening an issue or PR.

## Before You Start

1. **Open an issue first** for any non-trivial change. Saves you and the maintainer from wasted effort.
2. **Check [PROJECT_BRIEF.md](./PROJECT_BRIEF.md)** — it defines the current iteration's scope. Contributions outside the current phase will be deferred.
3. **No DRM-bypass or reverse-engineering code** — see the Non-Goals section in [PROJECT.md](./PROJECT.md).
4. **License compatibility**: any new dependency must be MIT-distribution-compatible. GPL-licensed deps are reviewed case-by-case and avoided when feasible.

## Development Setup

```bash
git clone <repository-url>
cd opiter
uv sync --all-groups
uv run pytest
uv run python -m opiter
```

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the module layout.

## Pull Request Guidelines

- **One concern per PR** — don't mix refactors with features
- **Tests for new features** — `pytest-qt` for UI, plain `pytest` for `core/`
- **Respect the UI/core boundary** — `core/` modules must not `import PySide6`
- **Commit message format**: `<type>: <short description>`
  - Types: `feat | fix | refactor | docs | test | chore | ci`
  - Example: `feat: add page rotation in viewer`
- **Keep PRs small and reviewable**. Large changes should be split.

## Code Style

- **Python 3.11+** features OK (pattern matching, `Self` type, etc.)
- **Type hints** on all public APIs
- **Docstrings** on public modules/classes/functions (Google style)
- **Comments**: English by default; Korean acceptable for Korean-specific logic (e.g., Hangul font handling)
- **Formatter / linter** (config TBD): plan to adopt `ruff format` + `ruff check`

## Reporting Bugs

When filing a bug, include:
- OS and version (e.g., Ubuntu 22.04, Windows 11 + WSLg)
- Python version (`python --version`)
- A minimal reproducer (steps + sample PDF if possible)
- Full error traceback if available

For PDFs that trigger crashes, please confirm you have the right to share the file before attaching.

## License

By contributing, you agree your code is licensed under [MIT](./LICENSE).

## Questions

Open a GitHub Discussion or issue.
