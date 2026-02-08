"""Runner implementation backed by the ``gh copilot`` CLI extension."""

from __future__ import annotations

import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from typing import Iterator

from gh_agent_funhouse.agent.runner import RunRef, RunResult, RunStatus, Runner
from gh_agent_funhouse.db import Run, get_session, init_db

# In-process registry of active subprocesses keyed by run_id.
_ACTIVE: dict[str, subprocess.Popen[str]] = {}


def _ensure_copilot_available() -> str:
    """Return the path to ``gh`` or raise with install instructions."""
    gh = shutil.which("gh")
    if gh is None:
        raise RuntimeError(
            "The GitHub CLI ('gh') was not found on $PATH.\n"
            "Install it from https://cli.github.com/ and run:\n"
            "  gh extension install github/gh-copilot"
        )

    result = subprocess.run(
        [gh, "copilot", "--help"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "The 'gh copilot' extension is not installed or not working.\n"
            "Install it with:\n"
            "  gh extension install github/gh-copilot\n"
            "Then try again."
        )
    return gh


class CopilotCLIRunner(Runner):
    """Run tasks via ``gh copilot`` in a local subprocess."""

    # ---- Runner interface --------------------------------------------------

    def start(
        self,
        task_id: str,
        instructions: str,
        task_type: str,
        repo: str,
    ) -> RunRef:
        gh = _ensure_copilot_available()

        prompt = (
            f"You are working on repository {repo}.\n"
            f"Task type: {task_type}\n\n"
            f"{instructions}"
        )

        proc = subprocess.Popen(
            [gh, "copilot", "suggest", "-t", "shell", prompt],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        run_id = uuid.uuid4().hex[:12]
        _ACTIVE[run_id] = proc

        ref = RunRef(
            run_id=run_id,
            runner_type="copilot-cli",
            task_id=task_id,
            started_at=datetime.now(timezone.utc),
        )

        self._save_run(ref)
        return ref

    def poll(self, ref: RunRef) -> RunResult:
        proc = _ACTIVE.get(ref.run_id)
        if proc is None:
            return RunResult(status=RunStatus.FAILED)

        retcode = proc.poll()
        if retcode is None:
            return RunResult(status=RunStatus.RUNNING)

        ended = datetime.now(timezone.utc)
        status = RunStatus.SUCCESS if retcode == 0 else RunStatus.FAILED
        result = RunResult(status=status, ended_at=ended)

        self._update_run(ref, result)
        _ACTIVE.pop(ref.run_id, None)
        return result

    def cancel(self, ref: RunRef) -> bool:
        proc = _ACTIVE.pop(ref.run_id, None)
        if proc is None:
            return False

        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

        self._update_run(
            ref,
            RunResult(status=RunStatus.CANCELLED, ended_at=datetime.now(timezone.utc)),
        )
        return True

    def logs(self, ref: RunRef) -> Iterator[str]:
        proc = _ACTIVE.get(ref.run_id)
        if proc is None:
            yield "(process not found — it may have already exited)"
            return

        if proc.stdout is None:
            yield "(no output captured)"
            return

        for line in proc.stdout:
            yield line.rstrip("\n")

    # ---- helpers -----------------------------------------------------------

    @staticmethod
    def _save_run(ref: RunRef) -> None:
        init_db()
        session = get_session()
        try:
            db_run = Run(
                task_id=int(ref.task_id),
                runner_type=ref.runner_type,
                status=RunStatus.RUNNING.value,
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
                if result.ended_at:
                    db_run.ended_at = result.ended_at
                session.commit()
        finally:
            session.close()
