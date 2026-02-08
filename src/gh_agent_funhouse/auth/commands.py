"""Typer CLI commands for GitHub authentication.

Registered as the ``ghfun auth`` sub-command group.
"""

from __future__ import annotations

import os
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from gh_agent_funhouse.auth.storage import get_storage
from gh_agent_funhouse.config import get_current_repo
from gh_agent_funhouse.github_client import GitHubClient

_console = Console()

auth_app = typer.Typer(
    name="auth",
    help="Manage GitHub authentication.",
    no_args_is_help=True,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_token(token: str) -> dict:
    """Call the GitHub ``/user`` endpoint and return the user payload.

    Raises :class:`typer.Exit` on failure.
    """
    try:
        client = GitHubClient(token)
        try:
            return client.get_user()
        finally:
            client.close()
    except Exception as exc:  # noqa: BLE001
        _console.print(f"[red]✗ Token validation failed:[/red] {exc}")
        raise typer.Exit(code=1) from None


# ---------------------------------------------------------------------------
# login
# ---------------------------------------------------------------------------


@auth_app.command()
def login(
    pat: Optional[str] = typer.Option(
        None,
        "--pat",
        help="Personal access token to store directly.",
    ),
    device_flow: bool = typer.Option(
        False,
        "--device-flow",
        help="Use GitHub Device Flow (OAuth) to authenticate.",
    ),
    client_id: Optional[str] = typer.Option(
        None,
        "--client-id",
        help="GitHub OAuth App client ID (required with --device-flow).",
    ),
) -> None:
    """Authenticate with GitHub and store the token."""
    token: str | None = None

    # --- PAT supplied directly ---
    if pat:
        token = pat

    # --- Device flow ---
    elif device_flow:
        if not client_id:
            _console.print(
                "[red]✗ --client-id is required when using --device-flow.[/red]"
            )
            raise typer.Exit(code=1)

        from gh_agent_funhouse.auth.device_flow import DeviceFlowError, run_device_flow

        try:
            token = run_device_flow(client_id)
        except DeviceFlowError as exc:
            _console.print(f"[red]✗ Device flow failed:[/red] {exc}")
            raise typer.Exit(code=1) from None

    # --- Fallback: env var → interactive prompt ---
    else:
        env_token = os.environ.get("GITHUB_TOKEN")
        if env_token:
            _console.print("[dim]Using token from GITHUB_TOKEN environment variable.[/dim]")
            token = env_token
        else:
            token = typer.prompt("Enter your GitHub personal access token", hide_input=True)

    if not token:
        _console.print("[red]✗ No token provided.[/red]")
        raise typer.Exit(code=1)

    # Validate
    user = _validate_token(token)
    username: str = user.get("login", "unknown")

    # Store
    storage = get_storage()
    storage.save_token(token)

    _console.print(
        Panel(
            f"[green]✓ Logged in as [bold]{username}[/bold][/green]",
            border_style="green",
        )
    )


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


@auth_app.command()
def status() -> None:
    """Show current authentication and repository status."""
    storage = get_storage()
    token = storage.load_token()

    if not token:
        _console.print("[yellow]Not logged in.[/yellow] Run [bold]ghfun auth login[/bold] to authenticate.")
        raise typer.Exit(code=1)

    # Determine token type heuristic
    if token.startswith("gho_"):
        token_type = "OAuth token"
    elif token.startswith("ghp_"):
        token_type = "Personal access token"
    elif token.startswith("ghu_"):
        token_type = "User-to-server token"
    elif token.startswith("ghs_"):
        token_type = "Server-to-server token"
    elif token.startswith("github_pat_"):
        token_type = "Fine-grained personal access token"
    else:
        token_type = "Token"

    # Validate against API
    try:
        client = GitHubClient(token)
        try:
            user = client.get_user()
        finally:
            client.close()
        username = user.get("login", "unknown")
    except Exception:  # noqa: BLE001
        username = None

    # Current repo context
    repo = get_current_repo()

    _console.print(Panel.fit(
        "\n".join([
            f"[bold]Token:[/bold]  {token_type} ({'valid' if username else '[red]invalid[/red]'})",
            f"[bold]User:[/bold]   {username or '[red]unknown[/red]'}",
            f"[bold]Repo:[/bold]   {repo or '[dim]not set[/dim]'}",
        ]),
        title="Auth Status",
        border_style="bright_blue",
    ))


# ---------------------------------------------------------------------------
# logout
# ---------------------------------------------------------------------------


@auth_app.command()
def logout(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
) -> None:
    """Remove the stored GitHub token."""
    if not yes:
        confirm = typer.confirm("Are you sure you want to log out?")
        if not confirm:
            _console.print("[dim]Cancelled.[/dim]")
            raise typer.Exit()

    storage = get_storage()
    deleted = storage.delete_token()

    if deleted:
        _console.print("[green]✓ Token removed successfully.[/green]")
    else:
        _console.print("[yellow]No stored token found.[/yellow]")
