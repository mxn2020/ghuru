# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-01-15

### Added

- Initial release of gh-agent-funhouse CLI/TUI tool.
- **Authentication**: GitHub Device Flow OAuth and Personal Access Token support with secure keyring/encrypted file storage.
- **Repository management**: `ghfun repo create`, `list`, `select`, and `bootstrap` commands.
- **Mission system**: YAML-based mission definitions with `ghfun mission init`, `push`, and `status`.
- **Agent runners**: Pluggable `Runner` interface with `GitHubWorkflowRunner` (workflow_dispatch) and `CopilotCLIRunner` (optional subprocess-based).
- **TUI dashboard**: Textual-based interactive dashboard showing missions, tasks, runs, and timeline.
- **Local tracking**: SQLite database with SQLAlchemy 2.0 ORM for missions, tasks, and runs.
- **Repo scaffolding**: `ghfun repo bootstrap` creates workflow template, issue templates, and docs structure via PR.
- **CLI**: Full command surface via Typer with Rich formatting and helpful error messages.
- **Documentation**: mkdocs-material site with architecture, auth, workflow, and mission format docs.
- **CI**: GitHub Actions workflow for ruff, mypy, pytest with coverage, and build check.

### Security

- Secure token storage via system keyring with Fernet-encrypted file fallback.
- Token redaction in all error output and logs.
- Rate limit handling with exponential backoff.
