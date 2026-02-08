"""Runner implementation backed by a GitHub Actions workflow dispatch."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Iterator

from gh_agent_funhouse.agent.runner import RunRef, RunResult, RunStatus, Runner
from gh_agent_funhouse.db import Run, Task, get_session, init_db
from gh_agent_funhouse.github_client import GitHubClient, get_client

_WORKFLOW_FILE = "ghfun-agent.yml"
_POLL_INTERVAL = 3.0
_MAX_DISCOVER_ATTEMPTS = 10

# GitHub conclusion → RunStatus
_STATUS_MAP: dict[str | None, RunStatus] = {
    "success": RunStatus.SUCCESS,
    "failure": RunStatus.FAILED,
    "cancelled": RunStatus.CANCELLED,
    "timed_out": RunStatus.FAILED,
    "action_required": RunStatus.RUNNING,
    "skipped": RunStatus.CANCELLED,
    "stale": RunStatus.FAILED,
    None: RunStatus.RUNNING,
}


def _parse_owner_repo(repo: str) -> tuple[str, str]:
    """Split ``'owner/repo'`` into its two components."""
    owner, _, name = repo.partition("/")
    if not name:
        raise ValueError(f"Expected 'owner/repo', got {repo!r}")
    return owner, name


class GitHubWorkflowRunner(Runner):
    """Trigger and track a GitHub Actions ``workflow_dispatch`` run."""

    def __init__(self, client: GitHubClient | None = None) -> None:
        self._client = client or get_client()

    # ---- Runner interface --------------------------------------------------

    def start(
        self,
        task_id: str,
        instructions: str,
        task_type: str,
        repo: str,
    ) -> RunRef:
        owner, repo_name = _parse_owner_repo(repo)

        # Record a timestamp *before* dispatching so we can find the new run.
        before_dispatch = datetime.now(timezone.utc)

        self._client.dispatch_workflow(
            owner,
            repo_name,
            _WORKFLOW_FILE,
            ref="main",
            inputs={
                "task_id": task_id,
                "task_type": task_type,
                "instructions": instructions,
            },
        )

        # GitHub does not return the run_id from dispatch — poll until it
        # appears in the list of recent runs.
        github_run_id: int | None = None
        for _ in range(_MAX_DISCOVER_ATTEMPTS):
            time.sleep(_POLL_INTERVAL)
            runs = self._client.get_workflow_runs(owner, repo_name, per_page=5)
            for run in runs.get("workflow_runs", []):
                created = run.get("created_at", "")
                if created and created >= before_dispatch.strftime("%Y-%m-%dT%H:%M:%SZ"):
                    github_run_id = run["id"]
                    break
            if github_run_id is not None:
                break

        run_id = uuid.uuid4().hex[:12]
        ref = RunRef(
            run_id=run_id,
            runner_type="workflow",
            task_id=task_id,
            github_run_id=github_run_id,
            started_at=datetime.now(timezone.utc),
        )

        # Persist to DB
        self._save_run(ref, RunStatus.PENDING if github_run_id is None else RunStatus.RUNNING)
        return ref

    def poll(self, ref: RunRef) -> RunResult:
        if ref.github_run_id is None:
            return RunResult(status=RunStatus.FAILED)

        owner, repo_name = self._owner_repo_from_ref(ref)
        data = self._client.get_workflow_run(owner, repo_name, ref.github_run_id)

        gh_status: str = data.get("status", "")
        conclusion: str | None = data.get("conclusion")

        if gh_status == "completed":
            status = _STATUS_MAP.get(conclusion, RunStatus.FAILED)
        elif gh_status in {"queued", "waiting", "pending", "requested"}:
            status = RunStatus.PENDING
        else:
            status = RunStatus.RUNNING

        result = RunResult(
            status=status,
            log_url=data.get("html_url"),
            ended_at=datetime.now(timezone.utc) if status not in (RunStatus.RUNNING, RunStatus.PENDING) else None,
        )

        self._update_run(ref, result)
        return result

    def cancel(self, ref: RunRef) -> bool:
        if ref.github_run_id is None:
            return False

        owner, repo_name = self._owner_repo_from_ref(ref)
        try:
            self._client.post(
                f"/repos/{owner}/{repo_name}/actions/runs/{ref.github_run_id}/cancel",
            )
        except RuntimeError:
            return False

        self._update_run(ref, RunResult(status=RunStatus.CANCELLED, ended_at=datetime.now(timezone.utc)))
        return True

    def logs(self, ref: RunRef) -> Iterator[str]:
        if ref.github_run_id is None:
            yield "No GitHub run ID available — dispatch may have failed."
            return

        owner, repo_name = self._owner_repo_from_ref(ref)
        try:
            resp = self._client.get(
                f"/repos/{owner}/{repo_name}/actions/runs/{ref.github_run_id}/logs",
                follow_redirects=True,
            )
            for line in resp.text.splitlines():
                yield line
        except RuntimeError as exc:
            yield f"Could not retrieve logs: {exc}"

    # ---- helpers -----------------------------------------------------------

    def _owner_repo_from_ref(self, ref: RunRef) -> tuple[str, str]:
        """Resolve owner/repo for a ref by looking up the task's mission."""
        init_db()
        session = get_session()
        try:
            task = session.query(Task).filter_by(id=int(ref.task_id)).first()
            if task and task.mission:
                return _parse_owner_repo(task.mission.repo_full_name)
        finally:
            session.close()
        raise RuntimeError("Cannot determine repository for this run")

    def _save_run(self, ref: RunRef, status: RunStatus) -> None:
        init_db()
        session = get_session()
        try:
            db_run = Run(
                task_id=int(ref.task_id),
                runner_type=ref.runner_type,
                status=status.value,
                github_run_id=ref.github_run_id,
                started_at=ref.started_at,
            )
            session.add(db_run)
            session.commit()
            ref.run_id = str(db_run.id)
        finally:
            session.close()

    @staticmethod
    def _update_run(ref: RunRef, result: RunResult) -> None:
        init_db()
        session = get_session()
        try:
            db_run = session.query(Run).filter_by(id=int(ref.run_id)).first()
            if db_run:
                db_run.status = result.status.value
                if result.log_url:
                    db_run.log_url = result.log_url
                if result.pr_url:
                    db_run.pr_url = result.pr_url
                if result.ended_at:
                    db_run.ended_at = result.ended_at
                session.commit()
        finally:
            session.close()
