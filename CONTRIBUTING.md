# Contributing to kgout

Thanks for your interest in contributing!

## Development Setup

```bash
git clone https://github.com/vybhavchaturvedi/kgout
cd kgout
pip install -e ".[dev,all]"
```

## Running Tests

```bash
pytest tests/ -v
```

## Code Standards

- Python 3.8+ compatible (no walrus operator, no `match` statements)
- Type hints on all public methods
- Docstrings on all public classes and methods (NumPy style)
- No hard dependencies in core — optional deps via extras only

## Pull Request Process

1. Fork and create a feature branch from `main`
2. Add tests for new functionality
3. Ensure all existing tests pass
4. Update README if adding user-facing features
5. Update CHANGELOG.md under `[Unreleased]`
6. Open a PR with a clear description of what and why

## Reporting Bugs

Open a GitHub issue with:
- Python version and OS
- Steps to reproduce
- Expected vs actual behavior
- Full traceback (mask any tokens/credentials!)

## Security Issues

See [SECURITY.md](SECURITY.md). Do **not** open public issues for vulnerabilities.
