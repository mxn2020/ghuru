# Architecture & Design

## Overview

gh-agent-funhouse is built around a simple pipeline:

```
Mission (YAML) → GitHub Issues → Agent Runner → Workflow → PR
```

1. A **Mission** defines structured work (tasks) in a YAML file.
2. Tasks are pushed to GitHub as **Issues** with standardized labels.
3. An **Agent Runner** executes each task using GitHub-native primitives.
4. Results appear as **Pull Requests** in the target repository.

## Why httpx Over PyGithub

We chose `httpx` for GitHub API access instead of PyGithub for several reasons:

- **Lighter dependency**: httpx is a general-purpose HTTP client, not GitHub-specific.
- **Async-ready**: httpx supports both sync and async modes, enabling future async improvements.
- **Direct control**: We make targeted API calls rather than loading full object graphs.
- **Fewer abstractions**: Easier to debug and understand what's happening on the wire.
- **Better rate limit handling**: We implement custom backoff logic tailored to our use case.

## Runner Abstraction

The `Runner` ABC defines a pluggable interface for executing tasks:

```python
class Runner(ABC):
    def start(self, task_id, instructions, task_type, repo) -> RunRef: ...
    def poll(self, ref: RunRef) -> RunResult: ...
    def cancel(self, ref: RunRef) -> bool: ...
    def logs(self, ref: RunRef) -> Iterator[str]: ...
```

### GitHubWorkflowRunner

The primary runner uses `workflow_dispatch` to trigger a GitHub Actions workflow (`ghfun-agent.yml`) that:

1. Reads task instructions from the dispatch inputs
2. Performs deterministic operations based on task type (scaffold docs, seed data, run linters)
3. Creates a PR with the results

This demonstrates the full agent orchestration pipeline without requiring AI access.

### CopilotCLIRunner

An optional runner that integrates with GitHub Copilot CLI (`gh copilot`) if installed:

1. Checks for `gh copilot` availability
2. Starts a subprocess with task instructions
3. Captures output and guides the user interactively
4. Degrades gracefully if Copilot CLI is not available

## Database Design

SQLite with SQLAlchemy 2.0 ORM stores:

- **AuthProfile**: Username and auth type metadata (not tokens)
- **RepoContext**: Selected repository with current flag
- **Mission**: Title, summary, status, linked tracking issue
- **Task**: Individual work items with type, priority, and GitHub issue link
- **Run**: Execution records with runner type, status, timing, and result links

## Future: Direct AI Adapter

The Runner abstraction is designed to support future AI-powered runners:

```python
class AIRunner(Runner):
    """Future runner that calls an AI API directly."""
    def start(self, task_id, instructions, task_type, repo):
        # Call AI API (e.g., OpenAI, Anthropic, local model)
        # Submit code changes via GitHub API
        ...
```

The clean interface means adding AI capabilities requires implementing a single class with four methods.

## Limitations

- **No direct AI integration yet**: v0.1 uses GitHub-native primitives only.
- **GitHub.com only**: Enterprise Server support is planned but not tested.
- **Single-repo missions**: Each mission targets one repository.
- **Sequential runs**: Agents run one task at a time (parallel runs planned for v0.3).
