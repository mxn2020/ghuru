# Contributing to gh-agent-funhouse

Thank you for your interest in contributing! This document provides guidelines for contributing to gh-agent-funhouse.

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Create a feature branch from `main`
4. Make your changes
5. Submit a pull request

## Development Setup

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install
git clone https://github.com/YOUR_USERNAME/ghuru.git
cd ghuru
uv sync --dev

# Verify setup
uv run ghfun --version
```

## Code Style

We use **ruff** for linting and formatting, and **mypy** for type checking:

```bash
# Lint
uv run ruff check src/ tests/

# Format
uv run ruff format src/ tests/

# Type check
uv run mypy src/
```

## Testing

We use **pytest** with coverage reporting:

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=gh_agent_funhouse --cov-report=term-missing

# Run specific test file
uv run pytest tests/unit/test_mission_schema.py
```

## Pull Request Process

1. Update documentation if your change affects user-facing behavior.
2. Add tests for new functionality.
3. Ensure all tests pass and linting/type checks are clean.
4. Update CHANGELOG.md with your changes under an `[Unreleased]` section.
5. Request review from a maintainer.

## Commit Messages

Use clear, descriptive commit messages:

- `feat: add multi-agent parallel runs`
- `fix: handle rate limit correctly in workflow runner`
- `docs: update auth setup instructions`
- `test: add integration tests for mission push`

## Reporting Issues

- Use GitHub Issues for bug reports and feature requests.
- Include reproduction steps for bugs.
- Check existing issues before creating a new one.

## Code of Conduct

Please note that this project has a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to abide by its terms.
