# Mission Format

Missions are defined in YAML files (default: `ghfun-mission.yml`) that describe structured work plans.

## Schema

```yaml
title: "Mission Title"
summary: "Brief description of the mission goal"
goal: "Detailed goal description"
acceptance_criteria:
  - "Criterion 1"
  - "Criterion 2"
tasks:
  - id: "task-001"
    title: "Task title"
    type: "docs"          # docs | code | tests | seed | ci
    priority: 1           # 1 (highest) to 5 (lowest)
    instructions: |
      Detailed instructions for this task.
      Can be multi-line.
personas:
  - name: "DocBot"
    emoji: "📝"
    role: "Documentation specialist"
```

## Fields

### Top-Level

| Field                | Type       | Required | Description                          |
| -------------------- | ---------- | -------- | ------------------------------------ |
| `title`              | string     | Yes      | Mission title                        |
| `summary`            | string     | Yes      | Brief summary                        |
| `goal`               | string     | No       | Detailed goal description            |
| `acceptance_criteria` | list[str] | No       | Criteria for mission completion      |
| `tasks`              | list[Task] | Yes      | Work items to execute                |
| `personas`           | list[Persona] | No    | Cosmetic agent personas              |

### Task

| Field          | Type   | Required | Description                              |
| -------------- | ------ | -------- | ---------------------------------------- |
| `id`           | string | Yes      | Unique identifier (e.g., "task-001")     |
| `title`        | string | Yes      | Human-readable task title                |
| `type`         | string | Yes      | One of: docs, code, tests, seed, ci      |
| `priority`     | int    | Yes      | 1 (highest) to 5 (lowest)               |
| `instructions` | string | Yes      | Detailed instructions for the agent      |

### Persona

| Field   | Type   | Required | Description                    |
| ------- | ------ | -------- | ------------------------------ |
| `name`  | string | Yes      | Persona display name           |
| `emoji` | string | Yes      | Emoji icon for the persona     |
| `role`  | string | Yes      | Role description               |

## Task Types

- **`docs`**: Documentation creation or updates
- **`code`**: Code implementation or refactoring
- **`tests`**: Test creation or expansion
- **`seed`**: Seed data, fixtures, or example files
- **`ci`**: CI/CD configuration or validation

## Validation Rules

1. `title` and `summary` must not be empty.
2. `tasks` must contain at least one task.
3. Each task must have a unique `id`.
4. Task `type` must be one of the allowed values.
5. Task `priority` must be between 1 and 5.

## Example

```yaml
title: "Set Up Project Documentation"
summary: "Create comprehensive docs for the API service"
goal: "Have a complete documentation site with API reference, guides, and examples"
acceptance_criteria:
  - "mkdocs site builds without errors"
  - "All API endpoints are documented"
  - "Getting started guide is complete"
tasks:
  - id: "task-001"
    title: "Scaffold docs directory"
    type: "docs"
    priority: 1
    instructions: |
      Create the docs/ directory with:
      - index.md (landing page)
      - getting-started.md (setup guide)
      - api-reference.md (endpoint docs)
  - id: "task-002"
    title: "Add API examples"
    type: "seed"
    priority: 2
    instructions: |
      Create example request/response files in docs/examples/
  - id: "task-003"
    title: "Set up docs CI"
    type: "ci"
    priority: 3
    instructions: |
      Add a GitHub Actions workflow to build and deploy docs on push to main
personas:
  - name: "DocBot"
    emoji: "📝"
    role: "Documentation specialist"
  - name: "TestBot"
    emoji: "🧪"
    role: "Quality assurance agent"
```

## GitHub Integration

When you run `ghfun mission push`, each task becomes a GitHub Issue with:

- Title: `[ghfun] {task.title}`
- Body: Task instructions + metadata
- Labels: `ghfun/task`, `ghfun/{task.type}`, `ghfun/priority-{task.priority}`

A "Mission Control" tracking issue links all task issues together.
