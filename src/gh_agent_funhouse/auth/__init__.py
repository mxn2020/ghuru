"""Authentication module for gh-agent-funhouse."""

from __future__ import annotations

from gh_agent_funhouse.auth.commands import auth_app
from gh_agent_funhouse.auth.storage import (
    FileStorage,
    KeyringStorage,
    TokenStorage,
    get_storage,
)

__all__ = [
    "FileStorage",
    "KeyringStorage",
    "TokenStorage",
    "auth_app",
    "get_storage",
]
