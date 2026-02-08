from __future__ import annotations

from gh_agent_funhouse.mission.schema import (
    MissionSpec,
    PersonaSpec,
    TaskSpec,
    load_mission,
    save_mission,
    validate_mission,
)


def _make_valid_mission() -> MissionSpec:
    return MissionSpec(
        title="Test Mission",
        summary="A test summary",
        goal="Deliver tests",
        acceptance_criteria=["All tests pass"],
        tasks=[
            TaskSpec(
                id="task-1",
                title="Write tests",
                type="tests",
                priority=1,
                instructions="Write unit tests for everything.",
            ),
        ],
        personas=[
            PersonaSpec(name="Tester", emoji="🧪", role="QA engineer"),
        ],
    )


def test_mission_spec_creation():
    m = _make_valid_mission()
    assert m.title == "Test Mission"
    assert len(m.tasks) == 1
    assert len(m.personas) == 1


def test_task_spec_creation():
    t = TaskSpec(id="t1", title="Do stuff", type="code", priority=3, instructions="Do it")
    assert t.id == "t1"
    assert t.type == "code"


def test_persona_spec_creation():
    p = PersonaSpec(name="Bot", emoji="🤖", role="coder")
    assert p.name == "Bot"


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "mission.yaml"
    original = _make_valid_mission()
    save_mission(original, path)
    loaded = load_mission(path)

    assert loaded.title == original.title
    assert loaded.summary == original.summary
    assert loaded.goal == original.goal
    assert loaded.acceptance_criteria == original.acceptance_criteria
    assert len(loaded.tasks) == len(original.tasks)
    assert loaded.tasks[0].id == original.tasks[0].id
    assert loaded.tasks[0].type == original.tasks[0].type
    assert len(loaded.personas) == len(original.personas)
    assert loaded.personas[0].name == original.personas[0].name


def test_validate_valid_mission():
    m = _make_valid_mission()
    errors = validate_mission(m)
    assert errors == []


def test_validate_missing_title():
    m = _make_valid_mission()
    m.title = ""
    errors = validate_mission(m)
    assert any("title" in e.lower() for e in errors)


def test_validate_invalid_task_type():
    m = _make_valid_mission()
    m.tasks[0].type = "banana"
    errors = validate_mission(m)
    assert any("invalid type" in e.lower() for e in errors)


def test_validate_duplicate_task_ids():
    m = _make_valid_mission()
    m.tasks.append(
        TaskSpec(
            id="task-1",
            title="Duplicate",
            type="code",
            priority=2,
            instructions="Dup instructions",
        )
    )
    errors = validate_mission(m)
    assert any("duplicate" in e.lower() for e in errors)
