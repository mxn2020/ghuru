"""`ghfun dashboard` sub-command group.

Registered in :mod:`gh_agent_funhouse.cli` as the ``dashboard`` sub-command.
"""

from __future__ import annotations

import typer

dashboard_app_typer = typer.Typer(
    name="dashboard",
    help="Interactive TUI dashboard for missions, tasks & runs.",
    invoke_without_command=True,
)


@dashboard_app_typer.callback()
def launch(
    ctx: typer.Context,
) -> None:
    """Launch the interactive TUI dashboard."""
    if ctx.invoked_subcommand is not None:
        return

    from gh_agent_funhouse.dashboard.app import FunhouseDashboard

    app = FunhouseDashboard()
    app.run()
