"""Typer CLI commands for mission management.

Registered as the ``ghfun mission`` sub-command group.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from gh_agent_funhouse.config import get_current_repo
from gh_agent_funhouse.db import Mission, Task, get_session, init_db
from gh_agent_funhouse.github_client import get_client
from gh_agent_funhouse.mission.schema import (
    MissionSpec,
    PersonaSpec,
    TaskSpec,
    load_mission,
    save_mission,
    validate_mission,
)

_console = Console()

MISSION_FILE = "ghfun-mission.yml"

mission_app = typer.Typer(
    name="mission",
    help="Manage project missions.",
    no_args_is_help=True,
)

# Label definitions for ghfun tasks
_GHFUN_LABELS: dict[str, dict[str, str]] = {
    "ghfun/mission": {"color": "6f42c1", "description": "gh-agent-funhouse mission tracking"},
    "ghfun/task": {"color": "0e8a16", "description": "gh-agent-funhouse task"},
    "ghfun/docs": {"color": "0075ca", "description": "Documentation task"},
    "ghfun/code": {"color": "e4e669", "description": "Code task"},
    "ghfun/tests": {"color": "d73a4a", "description": "Testing task"},
    "ghfun/seed": {"color": "f9d0c4", "description": "Seed data task"},
    "ghfun/ci": {"color": "bfdadc", "description": "CI/CD task"},
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_current_repo() -> tuple[str, str]:
    """Return the current ``(owner, repo)`` or exit with an error."""
    current = get_current_repo()
    if not current:
        _console.print(
            "[red]✗ No repository selected.[/red] "
            "Run [bold]ghfun repo select OWNER/REPO[/bold] first."
        )
        raise typer.Exit(code=1)
    owner, repo = current.split("/", 1)
    return owner, repo


def _mission_path() -> Path:
    return Path.cwd() / MISSION_FILE


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


@mission_app.command()
def init(
    title: str = typer.Option(..., "--title", "-t", help="Mission title."),
    summary: str = typer.Option(..., "--summary", "-s", help="Short mission summary."),
) -> None:
    """Create a new mission YAML file and register it in the local database."""
    init_db()

    current_repo = get_current_repo() or "owner/repo"
    mission_spec = MissionSpec(
        title=title,
        summary=summary,
        goal="Define the project goal here.",
        acceptance_criteria=[
            "All tasks completed successfully.",
            "Tests passing in CI.",
        ],
        tasks=[
            TaskSpec(
                id="docs-readme",
                title="Write project README",
                type="docs",
                priority=1,
                instructions="Create a comprehensive README.md covering setup, usage, and contributing.",
            ),
            TaskSpec(
                id="code-core",
                title="Implement core module",
                type="code",
                priority=2,
                instructions="Build the main application logic.",
            ),
            TaskSpec(
                id="tests-unit",
                title="Add unit tests",
                type="tests",
                priority=3,
                instructions="Write unit tests for all public functions.",
            ),
        ],
        personas=[
            PersonaSpec(name="Archie", emoji="🏗️", role="Architect"),
            PersonaSpec(name="Tessa", emoji="🧪", role="Tester"),
        ],
    )

    path = _mission_path()
    save_mission(mission_spec, path)

    # Persist to database
    session = get_session()
    try:
        db_mission = Mission(
            title=title,
            summary=summary,
            repo_full_name=current_repo,
            local_path=str(path),
            status="draft",
        )
        for task_spec in mission_spec.tasks:
            db_mission.tasks.append(
                Task(
                    title=task_spec.title,
                    task_type=task_spec.type,
                    priority=task_spec.priority,
                    instructions=task_spec.instructions,
                    status="todo",
                )
            )
        session.add(db_mission)
        session.commit()
    finally:
        session.close()

    _console.print(
        Panel(
            f"[green]✓ Mission [bold]{title}[/bold] created[/green]\n"
            f"  File: {path}\n"
            f"  Tasks: {len(mission_spec.tasks)}\n"
            f"  Repo: {current_repo}",
            title="Mission Initialized",
            border_style="green",
        )
    )


# ---------------------------------------------------------------------------
# push
# ---------------------------------------------------------------------------


@mission_app.command()
def push() -> None:
    """Push the local mission to GitHub as issues with ghfun/* labels."""
    init_db()

    path = _mission_path()
    if not path.exists():
        _console.print(
            f"[red]✗ Mission file not found:[/red] {path}\n"
            "Run [bold]ghfun mission init[/bold] first."
        )
        raise typer.Exit(code=1)

    mission_spec = load_mission(path)
    errors = validate_mission(mission_spec)
    if errors:
        _console.print("[red]✗ Mission validation failed:[/red]")
        for err in errors:
            _console.print(f"  • {err}")
        raise typer.Exit(code=1)

    owner, repo = _require_current_repo()
    client = get_client()
    session = get_session()

    try:
        # Find or create DB mission
        db_mission = (
            session.query(Mission)
            .filter_by(repo_full_name=f"{owner}/{repo}", title=mission_spec.title)
            .first()
        )
        if not db_mission:
            db_mission = Mission(
                title=mission_spec.title,
                summary=mission_spec.summary,
                repo_full_name=f"{owner}/{repo}",
                local_path=str(path),
                status="draft",
            )
            session.add(db_mission)
            session.flush()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=_console,
        ) as progress:
            # Ensure labels exist
            label_task = progress.add_task("Creating labels…", total=None)
            for label_name, label_info in _GHFUN_LABELS.items():
                try:
                    client.create_label(
                        owner,
                        repo,
                        label_name,
                        color=label_info["color"],
                        description=label_info["description"],
                    )
                except RuntimeError as exc:
                    if "422" not in str(exc):
                        raise
                    # Label already exists – that's fine
            progress.update(label_task, completed=True)

            # Create issues for each task
            issue_task = progress.add_task("Creating task issues…", total=len(mission_spec.tasks))
            task_issues: list[dict[str, object]] = []
            for task_spec in mission_spec.tasks:
                type_label = f"ghfun/{task_spec.type}"
                labels = ["ghfun/task", type_label]

                body = (
                    f"## {task_spec.title}\n\n"
                    f"**Type:** {task_spec.type}  \n"
                    f"**Priority:** {task_spec.priority}/5  \n\n"
                    f"### Instructions\n\n{task_spec.instructions}\n\n"
                    f"---\n"
                    f"*Part of mission: {mission_spec.title}*"
                )

                issue = client.create_issue(
                    owner, repo, task_spec.title, body=body, labels=labels,
                )
                issue_number: int = issue["number"]
                task_issues.append({"spec": task_spec, "number": issue_number, "url": issue["html_url"]})

                # Update or create DB task
                db_task = (
                    session.query(Task)
                    .filter_by(mission_id=db_mission.id, title=task_spec.title)
                    .first()
                )
                if db_task:
                    db_task.github_issue_number = issue_number
                else:
                    session.add(
                        Task(
                            mission_id=db_mission.id,
                            title=task_spec.title,
                            task_type=task_spec.type,
                            priority=task_spec.priority,
                            instructions=task_spec.instructions,
                            status="todo",
                            github_issue_number=issue_number,
                        )
                    )
                progress.advance(issue_task)

            # Create tracking issue
            tracking_task = progress.add_task("Creating tracking issue…", total=None)
            checklist = "\n".join(
                f"- [ ] #{ti['number']} — {ti['spec'].title}"  # type: ignore[index]
                for ti in task_issues
            )
            tracking_body = (
                f"# 🎯 Mission: {mission_spec.title}\n\n"
                f"**Summary:** {mission_spec.summary}\n\n"
                f"**Goal:** {mission_spec.goal}\n\n"
                f"## Acceptance Criteria\n\n"
                + "\n".join(f"- [ ] {c}" for c in mission_spec.acceptance_criteria)
                + "\n\n## Tasks\n\n"
                + checklist
                + "\n\n---\n*Managed by gh-agent-funhouse*"
            )
            tracking_issue = client.create_issue(
                owner,
                repo,
                f"🎯 Mission Control: {mission_spec.title}",
                body=tracking_body,
                labels=["ghfun/mission"],
            )
            db_mission.tracking_issue_number = tracking_issue["number"]
            db_mission.status = "pushed"
            progress.update(tracking_task, completed=True)

        session.commit()

        # Summary output
        _console.print()
        table = Table(title="Mission Pushed", border_style="green")
        table.add_column("Task", style="bold")
        table.add_column("Issue #", justify="right")
        table.add_column("URL")
        for ti in task_issues:
            table.add_row(
                str(ti["spec"].title),  # type: ignore[index]
                f"#{ti['number']}",
                str(ti["url"]),
            )
        table.add_row(
            "[bold]Tracking Issue[/bold]",
            f"#{tracking_issue['number']}",
            str(tracking_issue["html_url"]),
            style="bright_magenta",
        )
        _console.print(table)

    except typer.Exit:
        raise
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        _console.print(f"[red]✗ Push failed:[/red] {exc}")
        raise typer.Exit(code=1) from None
    finally:
        session.close()
        client.close()


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


@mission_app.command()
def status() -> None:
    """Show mission status with local data and live GitHub issue states."""
    init_db()

    path = _mission_path()
    if not path.exists():
        _console.print(
            f"[red]✗ No mission file found at [bold]{path}[/bold].[/red]\n"
            "Run [bold]ghfun mission init[/bold] first."
        )
        raise typer.Exit(code=1)

    mission_spec = load_mission(path)
    owner, repo = _require_current_repo()

    session = get_session()
    try:
        db_mission = (
            session.query(Mission)
            .filter_by(repo_full_name=f"{owner}/{repo}", title=mission_spec.title)
            .first()
        )

        if not db_mission:
            _console.print(
                "[yellow]⚠ Mission not found in database.[/yellow] "
                "Run [bold]ghfun mission init[/bold] or [bold]ghfun mission push[/bold]."
            )
            raise typer.Exit(code=1)

        # Fetch live issue states from GitHub when pushed
        github_states: dict[int, str] = {}
        if db_mission.status != "draft":
            try:
                client = get_client()
                try:
                    for db_task in db_mission.tasks:
                        if db_task.github_issue_number:
                            issue = client.get_issue(owner, repo, db_task.github_issue_number)
                            github_states[db_task.github_issue_number] = issue.get("state", "unknown")
                    if db_mission.tracking_issue_number:
                        tracking = client.get_issue(owner, repo, db_mission.tracking_issue_number)
                        github_states[db_mission.tracking_issue_number] = tracking.get("state", "unknown")
                finally:
                    client.close()
            except Exception:  # noqa: BLE001
                _console.print("[yellow]⚠ Could not fetch live issue states from GitHub.[/yellow]")

        # Header
        _console.print(
            Panel(
                f"[bold]{db_mission.title}[/bold]\n"
                f"{db_mission.summary}\n\n"
                f"Status: [bold]{db_mission.status}[/bold]  |  "
                f"Repo: {db_mission.repo_full_name}  |  "
                f"Tracking: "
                + (f"#{db_mission.tracking_issue_number}" if db_mission.tracking_issue_number else "—"),
                title="Mission",
                border_style="bright_blue",
            )
        )

        # Task table
        table = Table(title="Tasks", border_style="bright_blue")
        table.add_column("#", justify="right", style="dim")
        table.add_column("Title", style="bold")
        table.add_column("Type")
        table.add_column("Priority", justify="center")
        table.add_column("DB Status")
        table.add_column("Issue #", justify="right")
        table.add_column("GitHub", justify="center")

        done_count = 0
        for i, db_task in enumerate(db_mission.tasks, 1):
            issue_num = db_task.github_issue_number
            gh_state = github_states.get(issue_num, "—") if issue_num else "—"

            status_style = {
                "todo": "white",
                "running": "yellow",
                "done": "green",
                "failed": "red",
            }.get(db_task.status, "white")

            gh_style = {
                "open": "yellow",
                "closed": "green",
            }.get(gh_state, "dim")

            if db_task.status == "done" or gh_state == "closed":
                done_count += 1

            table.add_row(
                str(i),
                db_task.title,
                db_task.task_type,
                str(db_task.priority),
                f"[{status_style}]{db_task.status}[/{status_style}]",
                f"#{issue_num}" if issue_num else "—",
                f"[{gh_style}]{gh_state}[/{gh_style}]",
            )

        _console.print(table)

        # Progress summary
        total = len(db_mission.tasks)
        if total:
            pct = int(done_count / total * 100)
            bar_len = 20
            filled = int(bar_len * done_count / total)
            bar = "█" * filled + "░" * (bar_len - filled)
            _console.print(
                f"\n  Progress: [{bar}] {done_count}/{total} ({pct}%)\n"
            )

    finally:
        session.close()
