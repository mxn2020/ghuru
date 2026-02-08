"""Typer CLI commands for agent orchestration.

Registered as the ``ghfun agent`` sub-command group.
"""

from __future__ import annotations

import time

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from gh_agent_funhouse.agent.copilot_runner import CopilotCLIRunner
from gh_agent_funhouse.agent.runner import Runner, RunRef, RunStatus
from gh_agent_funhouse.agent.workflow_runner import GitHubWorkflowRunner
from gh_agent_funhouse.db import Run, Task, get_session, init_db

_console = Console()

agent_app = typer.Typer(
    name="agent",
    help="Run and manage coding agents.",
    no_args_is_help=True,
)

_RUNNER_CHOICES = {"workflow": "workflow", "copilot-cli": "copilot-cli"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_runner(runner_type: str) -> Runner:
    """Instantiate the requested runner back-end."""
    if runner_type == "copilot-cli":
        return CopilotCLIRunner()
    return GitHubWorkflowRunner()


def _status_style(status: str) -> str:
    return {
        "pending": "yellow",
        "running": "blue",
        "success": "green",
        "failed": "red",
        "cancelled": "dim",
    }.get(status, "white")


def _build_ref_from_db(db_run: Run) -> RunRef:
    """Reconstruct a :class:`RunRef` from a persisted :class:`Run`."""
    return RunRef(
        run_id=str(db_run.id),
        runner_type=db_run.runner_type,
        task_id=str(db_run.task_id),
        github_run_id=db_run.github_run_id,
        started_at=db_run.started_at or db_run.task.created_at,
    )


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------


@agent_app.command()
def run(
    task_id: int = typer.Option(..., "--task", help="Database ID of the task to run."),
    runner: str = typer.Option(
        "workflow",
        "--runner",
        help="Runner back-end (workflow | copilot-cli).",
    ),
) -> None:
    """Start an agent run for a given task."""
    if runner not in _RUNNER_CHOICES:
        _console.print(f"[red]✗ Unknown runner '{runner}'. Choose: workflow, copilot-cli[/red]")
        raise typer.Exit(code=1)

    init_db()
    session = get_session()
    try:
        task = session.query(Task).filter_by(id=task_id).first()
        if not task:
            _console.print(f"[red]✗ Task {task_id} not found in the database.[/red]")
            raise typer.Exit(code=1)

        repo = task.mission.repo_full_name
        backend = _build_runner(runner)

        _console.print(f"[bold]Starting {runner} run for task [cyan]#{task_id}[/cyan] …[/bold]")

        ref = backend.start(
            task_id=str(task.id),
            instructions=task.instructions,
            task_type=task.task_type,
            repo=repo,
        )

        # Mark task as running
        task.status = "running"
        session.commit()
    except typer.Exit:
        raise
    except Exception as exc:  # noqa: BLE001
        _console.print(f"[red]✗ Failed to start run:[/red] {exc}")
        raise typer.Exit(code=1) from None
    finally:
        session.close()

    _console.print(
        Panel(
            f"[green]✓ Run started[/green]\n"
            f"  Run ID:     {ref.run_id}\n"
            f"  Runner:     {ref.runner_type}\n"
            f"  Task:       #{ref.task_id}\n"
            f"  GitHub Run: {ref.github_run_id or '—'}",
            title="Agent Run",
            border_style="green",
        )
    )


# ---------------------------------------------------------------------------
# list-runs
# ---------------------------------------------------------------------------


@agent_app.command("list-runs")
def list_runs() -> None:
    """Show all agent runs recorded in the local database."""
    init_db()
    session = get_session()
    try:
        runs = session.query(Run).order_by(Run.id.desc()).all()
        if not runs:
            _console.print("[dim]No runs found.[/dim]")
            raise typer.Exit()

        table = Table(title="Agent Runs", border_style="bright_blue")
        table.add_column("ID", justify="right", style="bold")
        table.add_column("Task", justify="right")
        table.add_column("Runner")
        table.add_column("Status")
        table.add_column("Started")
        table.add_column("Ended")
        table.add_column("Links")

        for r in runs:
            style = _status_style(r.status)
            links_parts: list[str] = []
            if r.log_url:
                links_parts.append(f"[link={r.log_url}]logs[/link]")
            if r.pr_url:
                links_parts.append(f"[link={r.pr_url}]PR[/link]")

            table.add_row(
                str(r.id),
                str(r.task_id),
                r.runner_type,
                f"[{style}]{r.status}[/{style}]",
                r.started_at.strftime("%Y-%m-%d %H:%M") if r.started_at else "—",
                r.ended_at.strftime("%Y-%m-%d %H:%M") if r.ended_at else "—",
                " | ".join(links_parts) or "—",
            )

        _console.print(table)
    finally:
        session.close()


# ---------------------------------------------------------------------------
# watch
# ---------------------------------------------------------------------------


@agent_app.command()
def watch(
    run_id: int = typer.Argument(..., help="ID of the run to watch."),
) -> None:
    """Live-watch an agent run, polling every 5 seconds until completion."""
    init_db()
    session = get_session()
    try:
        db_run = session.query(Run).filter_by(id=run_id).first()
        if not db_run:
            _console.print(f"[red]✗ Run {run_id} not found.[/red]")
            raise typer.Exit(code=1)

        ref = _build_ref_from_db(db_run)
        backend = _build_runner(db_run.runner_type)
    finally:
        session.close()

    def _render(status: str, log_url: str | None) -> Panel:
        style = _status_style(status)
        body = (
            f"  Run:    {ref.run_id}\n"
            f"  Runner: {ref.runner_type}\n"
            f"  Status: [{style}]{status}[/{style}]\n"
            f"  Logs:   {log_url or '—'}"
        )
        return Panel(body, title=f"Watching Run #{run_id}", border_style=style)

    terminal_statuses = {RunStatus.SUCCESS, RunStatus.FAILED, RunStatus.CANCELLED}

    try:
        with Live(
            _render(db_run.status, db_run.log_url), console=_console, refresh_per_second=1
        ) as live:
            while True:
                result = backend.poll(ref)
                live.update(_render(result.status.value, result.log_url))
                if result.status in terminal_statuses:
                    break
                time.sleep(5)
    except KeyboardInterrupt:
        _console.print("\n[yellow]Stopped watching (Ctrl+C).[/yellow]")
        raise typer.Exit() from None

    _console.print(f"Run #{run_id} finished with status: [bold]{result.status.value}[/bold]")


# ---------------------------------------------------------------------------
# cancel
# ---------------------------------------------------------------------------


@agent_app.command()
def cancel(
    run_id: int = typer.Argument(..., help="ID of the run to cancel."),
) -> None:
    """Cancel an in-progress agent run."""
    init_db()
    session = get_session()
    try:
        db_run = session.query(Run).filter_by(id=run_id).first()
        if not db_run:
            _console.print(f"[red]✗ Run {run_id} not found.[/red]")
            raise typer.Exit(code=1)

        if db_run.status not in ("pending", "running"):
            _console.print(f"[yellow]Run {run_id} is already {db_run.status}.[/yellow]")
            raise typer.Exit()

        ref = _build_ref_from_db(db_run)
        backend = _build_runner(db_run.runner_type)
        ok = backend.cancel(ref)

        if ok:
            db_run.status = "cancelled"
            session.commit()
            _console.print(f"[green]✓ Run {run_id} cancelled.[/green]")
        else:
            _console.print(f"[red]✗ Could not cancel run {run_id}.[/red]")
            raise typer.Exit(code=1)
    except typer.Exit:
        raise
    except Exception as exc:  # noqa: BLE001
        _console.print(f"[red]✗ Cancel failed:[/red] {exc}")
        raise typer.Exit(code=1) from None
    finally:
        session.close()
