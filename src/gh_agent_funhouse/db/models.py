"""SQLAlchemy 2.0 ORM models for gh-agent-funhouse."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Shared declarative base for all models."""


# ---------------------------------------------------------------------------
# AuthProfile
# ---------------------------------------------------------------------------


class AuthProfile(Base):
    __tablename__ = "auth_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(255))
    auth_type: Mapped[str] = mapped_column(String(50))  # device_flow | pat
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# RepoContext
# ---------------------------------------------------------------------------


class RepoContext(Base):
    __tablename__ = "repo_contexts"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(511))
    is_current: Mapped[bool] = mapped_column(default=False)
    selected_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Mission
# ---------------------------------------------------------------------------


class Mission(Base):
    __tablename__ = "missions"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    summary: Mapped[str] = mapped_column(Text)
    repo_full_name: Mapped[str] = mapped_column(String(511))
    local_path: Mapped[str] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(
        String(50), default="draft",
    )  # draft | pushed | active | completed
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    tracking_issue_number: Mapped[Optional[int]] = mapped_column(default=None)

    tasks: Mapped[list[Task]] = relationship(
        back_populates="mission", cascade="all, delete-orphan",
    )


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id"))
    title: Mapped[str] = mapped_column(String(500))
    task_type: Mapped[str] = mapped_column(
        String(50),
    )  # docs | code | tests | seed | ci
    priority: Mapped[int] = mapped_column(default=3)
    instructions: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(50), default="todo",
    )  # todo | running | done | failed
    github_issue_number: Mapped[Optional[int]] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    mission: Mapped[Mission] = relationship(back_populates="tasks")
    runs: Mapped[list[Run]] = relationship(
        back_populates="task", cascade="all, delete-orphan",
    )


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"))
    runner_type: Mapped[str] = mapped_column(
        String(50),
    )  # workflow | copilot-cli
    status: Mapped[str] = mapped_column(
        String(50), default="pending",
    )  # pending | running | success | failed | cancelled
    github_run_id: Mapped[Optional[int]] = mapped_column(default=None)
    started_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    ended_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    log_url: Mapped[Optional[str]] = mapped_column(String(2048), default=None)
    pr_url: Mapped[Optional[str]] = mapped_column(String(2048), default=None)

    task: Mapped[Task] = relationship(back_populates="runs")
