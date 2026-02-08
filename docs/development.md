# Development Setup

## Prerequisites

- Python 3.12 or later
- [uv](https://github.com/astral-sh/uv) package manager

## Installation

```bash
# Clone the repository
git clone https://github.com/mxn2020/ghuru.git
cd ghuru

# Install dependencies (creates virtual environment automatically)
uv sync --dev

# Verify installation
uv run ghfun --version
```

## Running Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=gh_agent_funhouse --cov-report=term-missing

# Run specific test file
uv run pytest tests/unit/test_mission_schema.py

# Run specific test
uv run pytest tests/unit/test_mission_schema.py::test_valid_mission
```

## Linting

```bash
# Check for lint errors
uv run ruff check src/ tests/

# Auto-fix lint errors
uv run ruff check --fix src/ tests/

# Check formatting
uv run ruff format --check src/ tests/

# Auto-format
uv run ruff format src/ tests/
```

## Type Checking

```bash
uv run mypy src/
```

## Building Documentation

```bash
# Install docs dependencies
uv pip install mkdocs-material

# Serve docs locally
uv run mkdocs serve

# Build docs
uv run mkdocs build
```

## Project Structure

```
ghuru/
├── src/gh_agent_funhouse/     # Main package
│   ├── auth/                  # Authentication module
│   ├── repo/                  # Repository management
│   ├── mission/               # Mission system
│   ├── agent/                 # Agent runners
│   ├── dashboard/             # TUI dashboard
│   ├── db/                    # Database models
│   ├── cli.py                 # CLI entry point
│   ├── config.py              # Configuration
│   └── github_client.py       # GitHub API client
├── tests/                     # Test suite
│   ├── unit/                  # Unit tests
│   └── integration/           # Integration tests
├── docs/                      # Documentation source
└── .github/workflows/         # CI configuration
```

## Running the CLI During Development

```bash
# Run any ghfun command
uv run ghfun --help
uv run ghfun auth status
uv run ghfun repo list
```
