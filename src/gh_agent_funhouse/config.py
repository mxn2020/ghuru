"""Configuration management for gh-agent-funhouse.

Uses platformdirs for OS-appropriate config/data directories and a JSON
config file for persistent settings like the current repository context.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from platformdirs import user_config_dir, user_data_dir

APP_NAME = "gh-agent-funhouse"

# ---------------------------------------------------------------------------
# Directory helpers
# ---------------------------------------------------------------------------


def get_config_dir() -> Path:
    """Return the OS-appropriate configuration directory, creating it if needed."""
    path = Path(user_config_dir(APP_NAME))
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_data_dir() -> Path:
    """Return the OS-appropriate data directory, creating it if needed."""
    path = Path(user_data_dir(APP_NAME))
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_db_path() -> Path:
    """Return the path to the local SQLite database."""
    return get_data_dir() / "ghfun.db"


def get_config_path() -> Path:
    """Return the path to the JSON configuration file."""
    return get_config_dir() / "config.json"


# ---------------------------------------------------------------------------
# Low-level config read / write
# ---------------------------------------------------------------------------


def _read_config() -> dict[str, Any]:
    """Read the JSON config file and return its contents as a dict."""
    config_path = get_config_path()
    if not config_path.exists():
        return {}
    return json.loads(config_path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _write_config(data: dict[str, Any]) -> None:
    """Write *data* to the JSON config file."""
    config_path = get_config_path()
    config_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Current-repo helpers
# ---------------------------------------------------------------------------


def get_current_repo() -> str | None:
    """Return the currently configured ``owner/repo`` string, or *None*."""
    return _read_config().get("current_repo")


def set_current_repo(owner_repo: str) -> None:
    """Persist *owner_repo* (e.g. ``"octocat/Hello-World"``) as the active repo."""
    if "/" not in owner_repo:
        raise ValueError(f"Expected 'owner/repo' format, got: {owner_repo!r}")
    cfg = _read_config()
    cfg["current_repo"] = owner_repo
    _write_config(cfg)
