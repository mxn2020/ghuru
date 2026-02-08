from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from gh_agent_funhouse.db.models import (
    AuthProfile,
    Base,
    Mission,
    RepoContext,
    Run,
    Task,
)


def _make_engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", echo=False)
    Base.metadata.create_all(engine)
    return engine


def test_create_auth_profile(tmp_path):
    engine = _make_engine(tmp_path)
    with Session(engine) as session:
        profile = AuthProfile(username="octocat", auth_type="device_flow")
        session.add(profile)
        session.commit()
        assert profile.id is not None
        assert profile.username == "octocat"


def test_create_repo_context(tmp_path):
    engine = _make_engine(tmp_path)
    with Session(engine) as session:
        ctx = RepoContext(owner="octocat", name="Hello-World", full_name="octocat/Hello-World")
        session.add(ctx)
        session.commit()
        assert ctx.id is not None


def test_create_mission_with_tasks(tmp_path):
    engine = _make_engine(tmp_path)
    with Session(engine) as session:
        mission = Mission(
            title="Test mission",
            summary="A summary",
            repo_full_name="octocat/Hello-World",
            local_path="/tmp/test",
        )
        task = Task(
            title="Write code",
            task_type="code",
            priority=2,
            instructions="Implement feature X",
        )
        mission.tasks.append(task)
        session.add(mission)
        session.commit()

        assert mission.id is not None
        assert len(mission.tasks) == 1
        assert mission.tasks[0].mission_id == mission.id


def test_create_run(tmp_path):
    engine = _make_engine(tmp_path)
    with Session(engine) as session:
        mission = Mission(
            title="M",
            summary="S",
            repo_full_name="o/r",
            local_path="/tmp/m",
        )
        task = Task(
            title="T",
            task_type="code",
            priority=1,
            instructions="I",
        )
        mission.tasks.append(task)
        session.add(mission)
        session.flush()

        run = Run(task_id=task.id, runner_type="workflow", status="pending")
        session.add(run)
        session.commit()

        assert run.id is not None
        assert run.task_id == task.id


def test_init_db_creates_tables(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'init.db'}", echo=False)
    Base.metadata.create_all(engine)
    table_names = Base.metadata.tables.keys()
    assert "missions" in table_names
    assert "tasks" in table_names
    assert "runs" in table_names
    assert "auth_profiles" in table_names
    assert "repo_contexts" in table_names


def test_crud_mission_and_tasks(tmp_path):
    engine = _make_engine(tmp_path)
    with Session(engine) as session:
        mission = Mission(
            title="CRUD test",
            summary="Test CRUD",
            repo_full_name="owner/repo",
            local_path="/tmp/crud",
        )
        session.add(mission)
        session.flush()

        t1 = Task(
            mission_id=mission.id,
            title="Task A",
            task_type="docs",
            priority=1,
            instructions="Write docs",
        )
        t2 = Task(
            mission_id=mission.id,
            title="Task B",
            task_type="tests",
            priority=2,
            instructions="Write tests",
        )
        session.add_all([t1, t2])
        session.commit()

        queried = session.get(Mission, mission.id)
        assert queried is not None
        assert queried.title == "CRUD test"
        assert len(queried.tasks) == 2
        assert {t.title for t in queried.tasks} == {"Task A", "Task B"}
