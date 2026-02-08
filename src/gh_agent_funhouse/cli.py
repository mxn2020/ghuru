"""Main CLI entry point for gh-agent-funhouse (command: ``ghfun``).

Registers top-level options and all sub-command groups.
"""

from __future__ import annotations

import typer

from gh_agent_funhouse import __version__

# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="ghfun",
    help="gh-agent-funhouse – launch, track & manage GitHub-based coding agent workflows.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"gh-agent-funhouse {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-V",
        help="Show the version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """gh-agent-funhouse CLI root."""


# ---------------------------------------------------------------------------
# Sub-command groups (lazy imports keep startup fast)
# ---------------------------------------------------------------------------

from gh_agent_funhouse.auth.commands import auth_app  # noqa: E402
from gh_agent_funhouse.mission.commands import mission_app  # noqa: E402
from gh_agent_funhouse.repo.commands import repo_app  # noqa: E402
agent_app = typer.Typer(name="agent", help="Coding-agent orchestration.", no_args_is_help=True)
dashboard_app = typer.Typer(name="dashboard", help="TUI dashboard.", no_args_is_help=True)

app.add_typer(auth_app)
app.add_typer(repo_app)
app.add_typer(mission_app)
app.add_typer(agent_app)
app.add_typer(dashboard_app)
