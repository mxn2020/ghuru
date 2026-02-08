"""Abstract runner interface for coding agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator


class RunStatus(Enum):
    """Possible states for an agent run."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class RunRef:
    """Lightweight handle returned by :meth:`Runner.start`."""

    run_id: str
    runner_type: str
    task_id: str
    github_run_id: int | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class RunResult:
    """Snapshot of the current state of a run."""

    status: RunStatus
    log_url: str | None = None
    pr_url: str | None = None
    ended_at: datetime | None = None


class Runner(ABC):
    """Base class that all runner back-ends must implement."""

    @abstractmethod
    def start(
        self,
        task_id: str,
        instructions: str,
        task_type: str,
        repo: str,
    ) -> RunRef:
        """Launch a new agent run and return a reference handle."""
        ...

    @abstractmethod
    def poll(self, ref: RunRef) -> RunResult:
        """Check the current status of a run."""
        ...

    @abstractmethod
    def cancel(self, ref: RunRef) -> bool:
        """Request cancellation.  Return *True* if accepted."""
        ...

    @abstractmethod
    def logs(self, ref: RunRef) -> Iterator[str]:
        """Yield log lines produced by the run so far."""
        ...
