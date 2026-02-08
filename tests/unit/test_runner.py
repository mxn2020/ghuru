from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator

import pytest

from gh_agent_funhouse.agent.runner import RunRef, RunResult, RunStatus, Runner


def test_run_status_values():
    assert RunStatus.PENDING.value == "pending"
    assert RunStatus.RUNNING.value == "running"
    assert RunStatus.SUCCESS.value == "success"
    assert RunStatus.FAILED.value == "failed"
    assert RunStatus.CANCELLED.value == "cancelled"


def test_run_ref_creation_with_defaults():
    ref = RunRef(run_id="abc-123", runner_type="workflow", task_id="t-1")
    assert ref.run_id == "abc-123"
    assert ref.runner_type == "workflow"
    assert ref.task_id == "t-1"
    assert ref.github_run_id is None
    assert isinstance(ref.started_at, datetime)


def test_run_ref_creation_with_explicit_values():
    now = datetime.now(timezone.utc)
    ref = RunRef(
        run_id="r1", runner_type="copilot-cli", task_id="t-2",
        github_run_id=42, started_at=now,
    )
    assert ref.github_run_id == 42
    assert ref.started_at == now


def test_run_result_creation():
    result = RunResult(status=RunStatus.SUCCESS, log_url="https://example.com/log")
    assert result.status == RunStatus.SUCCESS
    assert result.log_url == "https://example.com/log"
    assert result.pr_url is None
    assert result.ended_at is None


def test_runner_abc_cannot_be_instantiated():
    with pytest.raises(TypeError):
        Runner()  # type: ignore[abstract]


def test_mock_runner_can_be_instantiated():
    class MockRunner(Runner):
        def start(self, task_id: str, instructions: str, task_type: str, repo: str) -> RunRef:
            return RunRef(run_id="mock", runner_type="mock", task_id=task_id)

        def poll(self, ref: RunRef) -> RunResult:
            return RunResult(status=RunStatus.SUCCESS)

        def cancel(self, ref: RunRef) -> bool:
            return True

        def logs(self, ref: RunRef) -> Iterator[str]:
            yield "log line"

    runner = MockRunner()
    ref = runner.start("t-1", "do stuff", "code", "owner/repo")
    assert ref.run_id == "mock"

    result = runner.poll(ref)
    assert result.status == RunStatus.SUCCESS

    assert runner.cancel(ref) is True
    assert list(runner.logs(ref)) == ["log line"]
