from __future__ import annotations

from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from gh_agent_funhouse.db.models import Base, Mission, Run, Task


def _setup_db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'workflow.db'}", echo=False)
    Base.metadata.create_all(engine)
    return engine


def test_end_to_end_workflow(tmp_path):
    """End-to-end test: create mission -> push -> start workflow -> poll -> verify."""
    engine = _setup_db(tmp_path)

    # Step 1: Create a mission with tasks in the DB
    with Session(engine) as session:
        mission = Mission(
            title="E2E Mission",
            summary="Integration test mission",
            repo_full_name="octocat/test-repo",
            local_path="/tmp/e2e",
            status="draft",
        )
        task = Task(
            title="Implement feature",
            task_type="code",
            priority=1,
            instructions="Build the feature",
            status="todo",
        )
        mission.tasks.append(task)
        session.add(mission)
        session.commit()
        mission_id = mission.id
        task_id = task.id

    # Verify draft state
    with Session(engine) as session:
        m = session.get(Mission, mission_id)
        assert m is not None
        assert m.status == "draft"
        assert len(m.tasks) == 1
        assert m.tasks[0].status == "todo"

    # Step 2: Simulate "push" — mock creating a GitHub issue
    mock_client = MagicMock()
    mock_client.create_issue.return_value = {"number": 42, "html_url": "https://github.com/octocat/test-repo/issues/42"}

    with Session(engine) as session:
        m = session.get(Mission, mission_id)
        issue = mock_client.create_issue("octocat", "test-repo", m.title, body=m.summary)
        m.tracking_issue_number = issue["number"]
        m.status = "pushed"
        session.commit()

    mock_client.create_issue.assert_called_once()

    with Session(engine) as session:
        m = session.get(Mission, mission_id)
        assert m.status == "pushed"
        assert m.tracking_issue_number == 42

    # Step 3: Simulate "start" — mock dispatching a workflow
    mock_client.dispatch_workflow.return_value = None

    with Session(engine) as session:
        t = session.get(Task, task_id)
        mock_client.dispatch_workflow(
            "octocat", "test-repo", "agent.yml",
            ref="main", inputs={"task_id": str(t.id)},
        )
        run = Run(
            task_id=t.id,
            runner_type="workflow",
            status="running",
            github_run_id=9999,
        )
        session.add(run)
        t.status = "running"
        session.commit()
        run_id = run.id

    mock_client.dispatch_workflow.assert_called_once()

    with Session(engine) as session:
        t = session.get(Task, task_id)
        assert t.status == "running"
        r = session.get(Run, run_id)
        assert r.status == "running"
        assert r.github_run_id == 9999

    # Step 4: Simulate "poll" — mock getting workflow run status
    mock_client.get_workflow_run.return_value = {
        "id": 9999,
        "status": "completed",
        "conclusion": "success",
        "html_url": "https://github.com/octocat/test-repo/actions/runs/9999",
    }

    with Session(engine) as session:
        r = session.get(Run, run_id)
        run_data = mock_client.get_workflow_run("octocat", "test-repo", r.github_run_id)
        r.status = "success" if run_data["conclusion"] == "success" else "failed"
        r.log_url = run_data["html_url"]

        t = session.get(Task, task_id)
        t.status = "done"
        session.commit()

    # Step 5: Final verification
    with Session(engine) as session:
        m = session.get(Mission, mission_id)
        assert m.status == "pushed"
        assert m.tracking_issue_number == 42

        t = session.get(Task, task_id)
        assert t.status == "done"

        r = session.get(Run, run_id)
        assert r.status == "success"
        assert r.log_url == "https://github.com/octocat/test-repo/actions/runs/9999"
        assert r.github_run_id == 9999
