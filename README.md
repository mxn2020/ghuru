# 🎪 gh-agent-funhouse

[![CI](https://github.com/mxn2020/ghuru/actions/workflows/ci.yml/badge.svg)](https://github.com/mxn2020/ghuru/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

**CLI/TUI tool to launch, track, and manage GitHub-based coding agent workflows.**

gh-agent-funhouse (`ghfun`) connects to your GitHub account, manages repositories, and orchestrates "coding agent" workflows using GitHub-native primitives: Issues, Pull Requests, and GitHub Actions `workflow_dispatch`. It provides a fun, polished TUI dashboard for visualizing the entire process.

> **How it works:** Missions are structured work plans defined in YAML. Each task becomes a GitHub Issue. Agent runners execute tasks via GitHub Actions workflows (or optionally GitHub Copilot CLI). Results appear as Pull Requests. No external AI is required — the v0.1 workflow runner performs deterministic operations. The clean `Runner` adapter interface makes it easy to add direct AI integration later.

## Features

- **🔐 Authentication**: Device Flow OAuth for GitHub Apps + PAT fallback with secure keyring/encrypted storage
- **📦 Repository Management**: Create, list, select, and bootstrap repositories with workflow templates
- **🎯 Mission System**: YAML-based mission definitions → GitHub Issues with labels and tracking
- **🤖 Agent Runners**: Pluggable `Runner` interface — GitHub Actions workflow runner (built-in) + Copilot CLI runner (optional)
- **📊 TUI Dashboard**: Real-time Textual-based visualization of missions, tasks, runs, and timeline
- **💾 Local Tracking**: SQLite database with SQLAlchemy 2.0 ORM for offline status tracking

## Install

```bash
pip install gh-agent-funhouse
```

**Or from source:**

```bash
git clone https://github.com/mxn2020/ghuru.git
cd ghuru
pip install .
```

**Development install (with uv):**

```bash
git clone https://github.com/mxn2020/ghuru.git
cd ghuru
uv sync --dev
```

## Quickstart

### 1. Authenticate

```bash
# Using a Personal Access Token (simplest)
ghfun auth login --pat ghp_YOUR_TOKEN_HERE

# Or via environment variable
export GITHUB_TOKEN=ghp_YOUR_TOKEN_HERE
ghfun auth login

# Or using Device Flow (for GitHub Apps)
ghfun auth login --device-flow --client-id YOUR_CLIENT_ID

# Check status
ghfun auth status
```

### 2. Select a repository

```bash
# List your repos
ghfun repo list

# Select an existing repo
ghfun repo select owner/repo-name

# Or create a new one
ghfun repo create --name my-project --description "My awesome project"
```

### 3. Bootstrap the repo

```bash
# Adds workflow template, issue templates, and docs structure via PR
ghfun repo bootstrap
```

### 4. Create and push a mission

```bash
# Create a mission YAML file
ghfun mission init --title "Build documentation" --summary "Set up project docs with mkdocs"

# Edit ghfun-mission.yml to customize tasks, then push to GitHub
ghfun mission push

# Check status
ghfun mission status
```

### 5. Run an agent

```bash
# Run a task using the GitHub Actions workflow runner
ghfun agent run --task task-001 --runner workflow

# Watch the run in real-time
ghfun agent watch 1

# List all runs
ghfun agent list-runs
```

### 6. Open the dashboard

```bash
ghfun dashboard
```

## Architecture

```
Mission (YAML) → GitHub Issues → Agent Runner → Workflow → PR
```

### Runner Abstraction

The pluggable `Runner` interface allows different execution backends:

| Runner | How it works | Requires |
|--------|-------------|----------|
| `workflow` (default) | Dispatches GitHub Actions workflow | Repo with `ghfun-agent.yml` |
| `copilot-cli` | Uses `gh copilot` subprocess | GitHub Copilot CLI installed |

Adding a new runner (e.g., direct AI) requires implementing four methods: `start()`, `poll()`, `cancel()`, `logs()`.

### Tech Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| CLI | Typer + Rich | Type-safe CLI with beautiful output |
| TUI | Textual | Full-featured terminal UI framework |
| GitHub API | httpx | Lightweight, async-ready HTTP client |
| Database | SQLite + SQLAlchemy 2.0 | Zero-config local persistence |
| Auth storage | keyring / Fernet | OS-native or encrypted file fallback |
| Packaging | uv + hatchling | Fast, modern Python packaging |

## Command Reference

### Authentication
| Command | Description |
|---------|------------|
| `ghfun auth login` | Authenticate with GitHub |
| `ghfun auth status` | Show authentication status |
| `ghfun auth logout` | Remove stored credentials |

### Repository
| Command | Description |
|---------|------------|
| `ghfun repo create --name NAME` | Create a new GitHub repository |
| `ghfun repo list` | List your repositories |
| `ghfun repo select OWNER/REPO` | Set current repository context |
| `ghfun repo bootstrap` | Add workflow templates via PR |

### Mission
| Command | Description |
|---------|------------|
| `ghfun mission init --title "..." --summary "..."` | Create mission YAML |
| `ghfun mission push` | Push mission as GitHub Issues |
| `ghfun mission status` | Show mission progress |

### Agent
| Command | Description |
|---------|------------|
| `ghfun agent run --task ID [--runner workflow]` | Start an agent run |
| `ghfun agent list-runs` | List all runs |
| `ghfun agent watch RUN_ID` | Live-watch a run |
| `ghfun agent cancel RUN_ID` | Cancel a running agent |

### Dashboard
| Command | Description |
|---------|------------|
| `ghfun dashboard` | Open the TUI dashboard |

## GitHub App Setup

To use Device Flow OAuth, create a GitHub App:

1. Go to **Settings → Developer settings → GitHub Apps → New GitHub App**
2. Set these permissions:
   - **Repository**: Read & Write
   - **Issues**: Read & Write
   - **Actions**: Read & Write
   - **Pull Requests**: Read & Write
   - **Metadata**: Read
3. Enable **Device Flow** under OAuth settings
4. Note the **Client ID**
5. Run: `ghfun auth login --device-flow --client-id YOUR_CLIENT_ID`

For PAT authentication, create a token with `repo` and `workflow` scopes.

## Development

```bash
# Install dev dependencies
uv sync --dev

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=gh_agent_funhouse --cov-report=term-missing

# Lint
uv run ruff check src/ tests/

# Format
uv run ruff format src/ tests/

# Type check
uv run mypy src/
```

## Roadmap

### v0.2 — AI Adapter Interface
- Direct AI runner implementation (OpenAI, Anthropic adapters)
- Configurable workflow templates
- Mission templates library

### v0.3 — Multi-Agent & Comparison
- Parallel agent runs for the same task
- Comparison dashboard with side-by-side diffs
- Web UI prototype

### v1.0 — Stable Release
- Plugin system for custom runners
- Full web UI with multi-user support
- GitHub Marketplace integration
- GitHub Enterprise Server support

## License

[MIT](LICENSE)

