"""Typer CLI commands for GitHub repository management.

Registered as the ``ghfun repo`` sub-command group.
"""

from __future__ import annotations

import base64
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from gh_agent_funhouse.config import get_current_repo, set_current_repo
from gh_agent_funhouse.github_client import GitHubClient, get_client
from gh_agent_funhouse.repo.templates import (
    ISSUE_TEMPLATE,
    MISSION_CONTROL_TEMPLATE,
    WORKFLOW_TEMPLATE,
)

_console = Console()

repo_app = typer.Typer(
    name="repo",
    help="Manage GitHub repositories.",
    no_args_is_help=True,
)


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


def _put_file(
    client: GitHubClient,
    owner: str,
    repo: str,
    path: str,
    content: str,
    message: str,
    branch: str,
) -> None:
    """Create or update a file via the GitHub Contents API."""
    encoded = base64.b64encode(content.encode()).decode()
    client.put(
        f"/repos/{owner}/{repo}/contents/{path}",
        json={
            "message": message,
            "content": encoded,
            "branch": branch,
        },
    )


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


@repo_app.command()
def create(
    name: str = typer.Option(..., "--name", help="Repository name."),
    private: bool = typer.Option(
        False,
        "--private/--public",
        help="Repository visibility (default: public).",
    ),
    description: Optional[str] = typer.Option(
        None, "--description", "-d", help="Short repository description."
    ),
) -> None:
    """Create a new GitHub repository and select it as current context."""
    client = get_client()
    try:
        repo_kwargs: dict[str, str] = {}
        if description is not None:
            repo_kwargs["description"] = description

        result = client.create_repo(name, private=private, **repo_kwargs)

        full_name: str = result["full_name"]
        set_current_repo(full_name)

        table = Table(title="Repository Created", border_style="green")
        table.add_column("Field", style="bold")
        table.add_column("Value")
        table.add_row("Name", result["full_name"])
        table.add_row("Visibility", "private" if result.get("private") else "public")
        table.add_row("Description", result.get("description") or "—")
        table.add_row("URL", result.get("html_url", ""))
        table.add_row("Context", f"[green]✓ selected as current repo[/green]")
        _console.print(table)
    except Exception as exc:  # noqa: BLE001
        _console.print(f"[red]✗ Failed to create repository:[/red] {exc}")
        raise typer.Exit(code=1) from None
    finally:
        client.close()


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


@repo_app.command("list")
def list_repos(
    limit: int = typer.Option(30, "--limit", "-n", help="Max repositories to show."),
) -> None:
    """List your GitHub repositories."""
    client = get_client()
    try:
        repos = client.list_repos(per_page=limit)

        if not repos:
            _console.print("[dim]No repositories found.[/dim]")
            return

        table = Table(title="Your Repositories", border_style="bright_blue")
        table.add_column("Name", style="bold")
        table.add_column("Visibility")
        table.add_column("Description", max_width=50)
        table.add_column("Updated")

        for r in repos:
            visibility = "private" if r.get("private") else "public"
            desc = r.get("description") or "—"
            updated = (r.get("updated_at") or "")[:10]
            table.add_row(r["full_name"], visibility, desc, updated)

        _console.print(table)
    except Exception as exc:  # noqa: BLE001
        _console.print(f"[red]✗ Failed to list repositories:[/red] {exc}")
        raise typer.Exit(code=1) from None
    finally:
        client.close()


# ---------------------------------------------------------------------------
# select
# ---------------------------------------------------------------------------


@repo_app.command()
def select(
    owner_repo: str = typer.Argument(
        ..., help="Repository in OWNER/REPO format."
    ),
) -> None:
    """Select a repository as the current working context."""
    if "/" not in owner_repo:
        _console.print(
            f"[red]✗ Invalid format:[/red] expected OWNER/REPO, got {owner_repo!r}"
        )
        raise typer.Exit(code=1)

    owner, repo = owner_repo.split("/", 1)
    client = get_client()
    try:
        result = client.get_repo(owner, repo)
        set_current_repo(result["full_name"])
        _console.print(
            Panel(
                f"[green]✓ Now using [bold]{result['full_name']}[/bold][/green]",
                border_style="green",
            )
        )
    except Exception as exc:  # noqa: BLE001
        _console.print(f"[red]✗ Repository not found or inaccessible:[/red] {exc}")
        raise typer.Exit(code=1) from None
    finally:
        client.close()


# ---------------------------------------------------------------------------
# bootstrap
# ---------------------------------------------------------------------------

_BOOTSTRAP_BRANCH = "ghfun/bootstrap"

_BOOTSTRAP_FILES: list[tuple[str, str, str]] = [
    (
        ".github/workflows/ghfun-agent.yml",
        WORKFLOW_TEMPLATE,
        "chore: add ghfun-agent workflow",
    ),
    (
        ".github/ISSUE_TEMPLATE/ghfun-task.md",
        ISSUE_TEMPLATE,
        "chore: add ghfun task issue template",
    ),
    (
        "docs/MISSION_CONTROL.md",
        MISSION_CONTROL_TEMPLATE,
        "chore: add mission control tracking doc",
    ),
]


@repo_app.command()
def bootstrap() -> None:
    """Add gh-agent-funhouse scaffolding files to the selected repo via a PR."""
    owner, repo = _require_current_repo()
    client = get_client()
    try:
        # Determine the default branch
        repo_info = client.get_repo(owner, repo)
        default_branch: str = repo_info.get("default_branch", "main")

        # Get the SHA of the default branch HEAD
        ref_data = client.get(
            f"/repos/{owner}/{repo}/git/ref/heads/{default_branch}"
        ).json()
        head_sha: str = ref_data["object"]["sha"]

        # Create the bootstrap branch
        _console.print(
            f"[dim]Creating branch [bold]{_BOOTSTRAP_BRANCH}[/bold] "
            f"from [bold]{default_branch}[/bold]…[/dim]"
        )
        try:
            client.post(
                f"/repos/{owner}/{repo}/git/refs",
                json={"ref": f"refs/heads/{_BOOTSTRAP_BRANCH}", "sha": head_sha},
            )
        except RuntimeError as exc:
            if "422" in str(exc) and "Reference already exists" in str(exc):
                _console.print(
                    f"[yellow]⚠ Branch {_BOOTSTRAP_BRANCH!r} already exists — "
                    "adding files to the existing branch.[/yellow]"
                )
            else:
                raise

        # Commit each scaffold file
        for path, content, commit_msg in _BOOTSTRAP_FILES:
            _console.print(f"  Adding [bold]{path}[/bold]…")
            _put_file(client, owner, repo, path, content, commit_msg, _BOOTSTRAP_BRANCH)

        # Create a pull request
        pr = client.create_pull_request(
            owner,
            repo,
            title="chore: bootstrap gh-agent-funhouse scaffolding",
            head=_BOOTSTRAP_BRANCH,
            base=default_branch,
            body=(
                "## 🚀 gh-agent-funhouse Bootstrap\n\n"
                "This PR adds the scaffolding files required by "
                "**gh-agent-funhouse**:\n\n"
                "- `.github/workflows/ghfun-agent.yml` — agent dispatch workflow\n"
                "- `.github/ISSUE_TEMPLATE/ghfun-task.md` — task issue template\n"
                "- `docs/MISSION_CONTROL.md` — mission control tracking document\n\n"
                "Merge this PR to activate the funhouse agent in your repository."
            ),
        )

        pr_url: str = pr.get("html_url", "")
        _console.print(
            Panel(
                f"[green]✓ Pull request created:[/green] [link={pr_url}]{pr_url}[/link]",
                title="Bootstrap Complete",
                border_style="green",
            )
        )
    except typer.Exit:
        raise
    except Exception as exc:  # noqa: BLE001
        _console.print(f"[red]✗ Bootstrap failed:[/red] {exc}")
        raise typer.Exit(code=1) from None
    finally:
        client.close()
