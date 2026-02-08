"""Textual TUI application for the gh-agent-funhouse dashboard.

Provides a rich, interactive terminal interface showing mission progress,
task status, recent runs, and a timeline feed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import DataTable, Footer, Header, Static

from gh_agent_funhouse.config import get_current_repo

# ---------------------------------------------------------------------------
# Status badge helpers
# ---------------------------------------------------------------------------

_TASK_STATUS_BADGE: dict[str, str] = {
    "done": "🟢 done",
    "failed": "🔴 failed",
    "running": "🟡 running",
    "todo": "⚪ todo",
}

_RUN_STATUS_BADGE: dict[str, str] = {
    "success": "🟢 success",
    "failed": "🔴 failed",
    "running": "🟡 running",
    "pending": "⚪ pending",
    "cancelled": "🔘 cancelled",
}

_MISSION_STATUS_EMOJI: dict[str, str] = {
    "draft": "📝",
    "pushed": "🚀",
    "active": "⚡",
    "completed": "🏁",
}


# ---------------------------------------------------------------------------
# Data-loading helpers (run in worker threads to avoid blocking the UI)
# ---------------------------------------------------------------------------


def _load_dashboard_data() -> dict[str, Any]:
    """Query the local DB for the current mission, tasks, and runs.

    Returns a dict with keys: repo, mission, tasks, runs, timeline.
    All DB access is confined to this function so it can safely run in a
    background thread.
    """
    from gh_agent_funhouse.db.engine import get_session
    from gh_agent_funhouse.db.models import Mission, Run, Task

    repo = get_current_repo()
    data: dict[str, Any] = {
        "repo": repo,
        "mission": None,
        "tasks": [],
        "runs": [],
        "timeline": [],
    }
    if not repo:
        return data

    with get_session() as session:
        mission = (
            session.query(Mission)
            .filter_by(repo_full_name=repo)
            .order_by(Mission.updated_at.desc())
            .first()
        )
        if not mission:
            return data

        data["mission"] = {
            "id": mission.id,
            "title": mission.title,
            "summary": mission.summary,
            "status": mission.status,
            "tracking_issue": mission.tracking_issue_number,
        }

        tasks = (
            session.query(Task)
            .filter_by(mission_id=mission.id)
            .order_by(Task.priority, Task.id)
            .all()
        )
        for t in tasks:
            data["tasks"].append(
                {
                    "id": t.id,
                    "title": t.title,
                    "type": t.task_type,
                    "status": t.status,
                }
            )

        runs = (
            session.query(Run)
            .join(Task, Run.task_id == Task.id)
            .filter(Task.mission_id == mission.id)
            .order_by(Run.id.desc())
            .limit(20)
            .all()
        )
        for r in runs:
            data["runs"].append(
                {
                    "id": r.id,
                    "task_id": r.task_id,
                    "runner": r.runner_type,
                    "status": r.status,
                    "started": r.started_at,
                    "ended": r.ended_at,
                    "log_url": r.log_url,
                    "pr_url": r.pr_url,
                }
            )

        # Build a simple timeline from tasks + runs
        timeline: list[dict[str, Any]] = []
        for t in tasks:
            timeline.append(
                {
                    "time": t.updated_at,
                    "icon": _TASK_STATUS_BADGE.get(t.status, ""),
                    "text": f"Task #{t.id} '{t.title}' → {t.status}",
                }
            )
        for r in runs:
            ts = r.ended_at or r.started_at or datetime.now(timezone.utc)
            timeline.append(
                {
                    "time": ts,
                    "icon": _RUN_STATUS_BADGE.get(r.status, ""),
                    "text": (
                        f"Run #{r.id} ({r.runner_type}) → {r.status}"
                    ),
                }
            )
        timeline.sort(key=lambda e: e["time"], reverse=True)
        data["timeline"] = timeline[:30]

    return data


# ---------------------------------------------------------------------------
# Widgets
# ---------------------------------------------------------------------------


class RepoHeader(Static):
    """Displays the currently selected repository."""

    repo: reactive[str] = reactive("(none)")

    def render(self) -> str:  # type: ignore[override]
        return f"🎯 Repository: [bold cyan]{self.repo}[/bold cyan]"


class MissionPanel(Static):
    """Shows mission title, summary, status, and a text-based progress bar."""

    DEFAULT_CSS = """
    MissionPanel {
        height: auto;
        padding: 1 2;
        background: $surface;
        border: round $primary;
    }
    """

    def update_mission(
        self, mission: dict[str, Any] | None, tasks: list[dict[str, Any]]
    ) -> None:
        if not mission:
            self.update("🎪 [dim]No active mission - create one with [bold]ghfun mission init[/bold][/dim]")
            return

        emoji = _MISSION_STATUS_EMOJI.get(mission["status"], "")
        done = sum(1 for t in tasks if t["status"] == "done")
        total = len(tasks) or 1
        pct = int(done / total * 100)
        bar_filled = "█" * (pct // 5)
        bar_empty = "░" * (20 - pct // 5)

        tracking = ""
        if mission.get("tracking_issue"):
            tracking = f"  🔗 Issue #{mission['tracking_issue']}"

        self.update(
            f"{emoji} [bold]{mission['title']}[/bold]\n"
            f"[dim]{mission['summary'][:120]}[/dim]\n"
            f"Status: [bold]{mission['status']}[/bold]{tracking}\n"
            f"Progress: [green]{bar_filled}[/green][dim]{bar_empty}[/dim] {pct}% ({done}/{total})"
        )


class TasksTable(DataTable):
    """DataTable showing all tasks for the current mission."""

    DEFAULT_CSS = """
    TasksTable {
        height: 1fr;
        border: round $secondary;
    }
    """

    def on_mount(self) -> None:
        self.add_columns("ID", "Title", "Type", "Status")
        self.cursor_type = "row"

    def load_tasks(self, tasks: list[dict[str, Any]]) -> None:
        self.clear()
        for t in tasks:
            badge = _TASK_STATUS_BADGE.get(t["status"], t["status"])
            self.add_row(str(t["id"]), t["title"][:50], t["type"], badge)


class RunsPanel(Static):
    """Displays recent workflow/agent runs."""

    DEFAULT_CSS = """
    RunsPanel {
        height: 1fr;
        padding: 1 2;
        background: $surface;
        border: round $accent;
        overflow-y: auto;
    }
    """

    def load_runs(self, runs: list[dict[str, Any]]) -> None:
        if not runs:
            self.update("[dim]No runs recorded yet.[/dim]")
            return
        lines: list[str] = []
        for r in runs[:10]:
            badge = _RUN_STATUS_BADGE.get(r["status"], r["status"])
            link = ""
            if r.get("pr_url"):
                link = f" [link={r['pr_url']}]PR[/link]"
            elif r.get("log_url"):
                link = f" [link={r['log_url']}]logs[/link]"
            started = ""
            if r.get("started"):
                started = f" {r['started']:%H:%M:%S}"
            lines.append(
                f"  {badge}  Run #{r['id']} [{r['runner']}]{started}{link}"
            )
        self.update("\n".join(lines))


class TimelineFeed(Static):
    """Scrollable feed of recent activity."""

    DEFAULT_CSS = """
    TimelineFeed {
        height: 1fr;
        padding: 1 2;
        background: $surface;
        border: round $warning;
        overflow-y: auto;
    }
    """

    def load_events(self, events: list[dict[str, Any]]) -> None:
        if not events:
            self.update("[dim]No activity yet – launch an agent![/dim]")
            return
        lines: list[str] = []
        for ev in events[:15]:
            ts = ev["time"]
            time_str = ts.strftime("%m/%d %H:%M") if ts else ""
            lines.append(f"  [dim]{time_str}[/dim] {ev['icon']} {ev['text']}")
        self.update("\n".join(lines))


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

_APP_CSS = """
Screen {
    layout: vertical;
}

#top-bar {
    height: 3;
    padding: 0 2;
    background: $primary-background;
}

#main-area {
    height: 1fr;
}

#left-col {
    width: 2fr;
}

#right-col {
    width: 1fr;
}

#mission-panel {
    height: auto;
    max-height: 8;
}

#tasks-table {
    height: 1fr;
}

#runs-panel {
    height: 1fr;
}

#timeline-feed {
    height: 1fr;
}
"""


class FunhouseDashboard(App):
    """🎪 gh-agent-funhouse interactive dashboard."""

    TITLE = "🎪 gh-agent-funhouse Dashboard"
    CSS = _APP_CSS
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(RepoHeader(id="repo-header"), id="top-bar")
        with Horizontal(id="main-area"):
            with Vertical(id="left-col"):
                yield MissionPanel(id="mission-panel")
                yield TasksTable(id="tasks-table")
            with Vertical(id="right-col"):
                yield RunsPanel("🏃 [bold]Recent Runs[/bold]\n", id="runs-panel")
                yield TimelineFeed("📜 [bold]Timeline[/bold]\n", id="timeline-feed")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_data()
        self.set_interval(30, self.refresh_data)

    def action_refresh(self) -> None:
        """Handle the 'r' keybinding."""
        self.refresh_data()

    @work(thread=True)
    def refresh_data(self) -> None:
        """Load data from the database in a worker thread, then update widgets."""
        try:
            data = _load_dashboard_data()
        except Exception:
            data = {
                "repo": get_current_repo(),
                "mission": None,
                "tasks": [],
                "runs": [],
                "timeline": [],
            }
        self.call_from_thread(self._apply_data, data)

    def _apply_data(self, data: dict[str, Any]) -> None:
        """Update all widgets with freshly loaded data (runs on the main thread)."""
        repo_header = self.query_one("#repo-header", RepoHeader)
        repo_header.repo = data["repo"] or "(no repo selected - run ghfun repo select)"

        mission_panel = self.query_one("#mission-panel", MissionPanel)
        mission_panel.update_mission(data["mission"], data["tasks"])

        tasks_table = self.query_one("#tasks-table", TasksTable)
        tasks_table.load_tasks(data["tasks"])

        runs_panel = self.query_one("#runs-panel", RunsPanel)
        runs_panel.load_runs(data["runs"])

        timeline_feed = self.query_one("#timeline-feed", TimelineFeed)
        timeline_feed.load_events(data["timeline"])
