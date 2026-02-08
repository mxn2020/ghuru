"""Mission YAML schema: dataclasses, loader, saver, and validator."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class PersonaSpec:
    """Cosmetic agent persona attached to a mission."""

    name: str
    emoji: str
    role: str


@dataclass
class TaskSpec:
    """A single task within a mission."""

    id: str
    title: str
    type: str  # docs | code | tests | seed | ci
    priority: int  # 1-5
    instructions: str


@dataclass
class MissionSpec:
    """Top-level mission specification loaded from / saved to YAML."""

    title: str
    summary: str
    goal: str
    acceptance_criteria: list[str] = field(default_factory=list)
    tasks: list[TaskSpec] = field(default_factory=list)
    personas: list[PersonaSpec] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _parse_task(data: dict[str, Any]) -> TaskSpec:
    return TaskSpec(
        id=str(data["id"]),
        title=str(data["title"]),
        type=str(data["type"]),
        priority=int(data["priority"]),
        instructions=str(data["instructions"]),
    )


def _parse_persona(data: dict[str, Any]) -> PersonaSpec:
    return PersonaSpec(
        name=str(data["name"]),
        emoji=str(data["emoji"]),
        role=str(data["role"]),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

VALID_TASK_TYPES = {"docs", "code", "tests", "seed", "ci"}


def load_mission(path: Path) -> MissionSpec:
    """Parse a YAML file into a :class:`MissionSpec`."""
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))

    return MissionSpec(
        title=str(raw["title"]),
        summary=str(raw["summary"]),
        goal=str(raw.get("goal", "")),
        acceptance_criteria=[str(c) for c in raw.get("acceptance_criteria", [])],
        tasks=[_parse_task(t) for t in raw.get("tasks", [])],
        personas=[_parse_persona(p) for p in raw.get("personas", [])],
    )


def save_mission(mission: MissionSpec, path: Path) -> None:
    """Write a :class:`MissionSpec` to a YAML file."""
    data = asdict(mission)
    path.write_text(
        yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def validate_mission(mission: MissionSpec) -> list[str]:
    """Return a list of validation errors (empty means valid)."""
    errors: list[str] = []

    if not mission.title.strip():
        errors.append("Mission title is required.")
    if not mission.summary.strip():
        errors.append("Mission summary is required.")
    if not mission.goal.strip():
        errors.append("Mission goal is required.")
    if not mission.acceptance_criteria:
        errors.append("At least one acceptance criterion is required.")
    if not mission.tasks:
        errors.append("At least one task is required.")

    seen_ids: set[str] = set()
    for i, task in enumerate(mission.tasks):
        prefix = f"Task #{i + 1} ({task.id!r})"
        if not task.id.strip():
            errors.append(f"{prefix}: task id is required.")
        if task.id in seen_ids:
            errors.append(f"{prefix}: duplicate task id.")
        seen_ids.add(task.id)

        if not task.title.strip():
            errors.append(f"{prefix}: title is required.")
        if task.type not in VALID_TASK_TYPES:
            errors.append(
                f"{prefix}: invalid type {task.type!r}; expected one of {sorted(VALID_TASK_TYPES)}."
            )
        if not (1 <= task.priority <= 5):
            errors.append(f"{prefix}: priority must be 1-5, got {task.priority}.")
        if not task.instructions.strip():
            errors.append(f"{prefix}: instructions are required.")

    return errors
