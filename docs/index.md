# gh-agent-funhouse

**CLI/TUI tool to launch, track, and manage GitHub-based coding agent workflows.**

gh-agent-funhouse (`ghfun`) connects to your GitHub account, manages repositories, and orchestrates "coding agent" workflows using GitHub-native primitives: Issues, Pull Requests, and GitHub Actions `workflow_dispatch`.

## Key Features

- **Authentication**: Device Flow OAuth for GitHub Apps, or PAT fallback
- **Repository Management**: Create, list, select, and bootstrap repositories
- **Mission System**: Define structured work plans in YAML, push as GitHub Issues
- **Agent Runners**: Pluggable runner interface with GitHub Actions workflow and Copilot CLI support
- **TUI Dashboard**: Real-time Textual-based visualization of missions, tasks, and runs
- **Local Tracking**: SQLite database for offline status tracking

## Quick Start

```bash
# Install
pip install gh-agent-funhouse

# Authenticate
ghfun auth login

# Select a repository
ghfun repo select owner/repo

# Bootstrap the repo with workflow templates
ghfun repo bootstrap

# Create and push a mission
ghfun mission init --title "Build docs site" --summary "Set up mkdocs documentation"
ghfun mission push

# Launch an agent run
ghfun agent run --task task-001 --runner workflow

# Open the dashboard
ghfun dashboard
```

## Architecture

See the [Design](design.md) page for a full architecture overview.
