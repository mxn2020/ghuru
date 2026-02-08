"""Agent orchestration package for gh-agent-funhouse."""

from __future__ import annotations

from gh_agent_funhouse.agent.commands import agent_app
from gh_agent_funhouse.agent.copilot_runner import CopilotCLIRunner
from gh_agent_funhouse.agent.runner import RunRef, RunResult, RunStatus, Runner
from gh_agent_funhouse.agent.workflow_runner import GitHubWorkflowRunner

__all__ = [
    "CopilotCLIRunner",
    "GitHubWorkflowRunner",
    "RunRef",
    "RunResult",
    "RunStatus",
    "Runner",
    "agent_app",
]
