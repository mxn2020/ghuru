# GitHub Workflow Runner

The `GitHubWorkflowRunner` is the primary agent runner. It uses GitHub Actions `workflow_dispatch` to execute tasks.

## How It Works

1. **Dispatch**: `ghfun agent run` triggers the `ghfun-agent.yml` workflow via the GitHub API's `workflow_dispatch` endpoint.

2. **Execution**: The workflow reads task parameters from dispatch inputs and performs operations based on the task type.

3. **Result**: The workflow creates a Pull Request with the results of the task.

## Workflow Template

The `ghfun-agent.yml` workflow is installed via `ghfun repo bootstrap`. It supports these task types:

### `docs` - Documentation Scaffolding

Creates a `docs/` directory structure with placeholder files:
- `docs/index.md`
- `docs/getting-started.md`
- `docs/api-reference.md`

### `seed` - Seed Data Generation

Creates sample data files based on the task instructions:
- JSON fixtures
- Configuration templates
- Example files

### `ci` - CI/CD Setup

Validates and runs existing CI configurations:
- Runs linters if configured
- Runs tests if configured
- Reports results

### `code` - Code Generation

Creates code scaffolding based on instructions:
- Module structure
- Interface definitions
- Boilerplate files

### `tests` - Test Scaffolding

Creates test file structure:
- Test directory setup
- Test file templates
- pytest configuration

## Workflow Inputs

The workflow accepts these `workflow_dispatch` inputs:

| Input          | Type   | Description                        |
| -------------- | ------ | ---------------------------------- |
| `task_id`      | string | Unique task identifier             |
| `task_type`    | choice | One of: docs, code, tests, seed, ci |
| `instructions` | string | Detailed task instructions          |

## Monitoring Runs

```bash
# Watch a run in real-time
ghfun agent watch RUN_ID

# List all runs
ghfun agent list-runs

# Cancel a running agent
ghfun agent cancel RUN_ID
```

## Limitations

- The workflow performs **deterministic operations only** — no AI or LLM calls.
- Task instructions are interpreted literally by shell scripts in the workflow.
- Complex code generation requires the future AI adapter integration.
- Workflow runs are subject to GitHub Actions usage limits.

## Customizing the Workflow

After `ghfun repo bootstrap`, you can edit `.github/workflows/ghfun-agent.yml` directly in your repository to customize behavior for your project's needs.
