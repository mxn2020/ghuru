"""Token storage abstraction for gh-agent-funhouse.

Provides a :class:`TokenStorage` protocol with two concrete implementations:
:class:`KeyringStorage` (preferred) and :class:`FileStorage` (fallback using
Fernet-encrypted files).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from rich.console import Console

if TYPE_CHECKING:
    from pathlib import Path

    from cryptography.fernet import Fernet

from gh_agent_funhouse.config import get_config_dir

_console = Console(stderr=True)

SERVICE_NAME = "gh-agent-funhouse"
_TOKEN_USERNAME = "github-token"
_KEY_FILENAME = "storage.key"
_TOKEN_FILENAME = "token.enc"


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class TokenStorage(Protocol):
    """Abstract interface for persisting a GitHub token."""

    def save_token(self, token: str) -> None:
        """Persist *token* to the backing store."""
        ...

    def load_token(self) -> str | None:
        """Return the stored token, or ``None`` if absent."""
        ...

    def delete_token(self) -> bool:
        """Remove the stored token.  Return ``True`` if a token was deleted."""
        ...


# ---------------------------------------------------------------------------
# Keyring implementation
# ---------------------------------------------------------------------------


class KeyringStorage:
    """Store the token in the OS keyring via the :mod:`keyring` library."""

    def __init__(self, service_name: str = SERVICE_NAME) -> None:
        self._service = service_name

    def save_token(self, token: str) -> None:
        import keyring

        keyring.set_password(self._service, _TOKEN_USERNAME, token)

    def load_token(self) -> str | None:
        import keyring

        return keyring.get_password(self._service, _TOKEN_USERNAME)

    def delete_token(self) -> bool:
        import keyring

        if self.load_token() is None:
            return False
        keyring.delete_password(self._service, _TOKEN_USERNAME)
        return True


# ---------------------------------------------------------------------------
# Encrypted-file implementation
# ---------------------------------------------------------------------------


class FileStorage:
    """Store a Fernet-encrypted token on disk.

    The encryption key is kept in a separate file inside the platformdirs
    config directory with ``0o600`` permissions.  If the key file does not
    exist it is generated automatically.
    """

    def __init__(self, config_dir: Path | None = None) -> None:
        self._config_dir = config_dir or get_config_dir()
        self._key_path = self._config_dir / _KEY_FILENAME
        self._token_path = self._config_dir / _TOKEN_FILENAME

    # -- key management ------------------------------------------------------

    def _ensure_key(self) -> bytes:
        """Return the Fernet key, creating it if necessary."""
        if self._key_path.exists():
            return self._key_path.read_bytes()

        from cryptography.fernet import Fernet

        key = Fernet.generate_key()
        self._config_dir.mkdir(parents=True, exist_ok=True)

        # Write atomically-ish and restrict permissions.
        self._key_path.write_bytes(key)
        os.chmod(self._key_path, 0o600)
        return key

    def _fernet(self) -> Fernet:
        from cryptography.fernet import Fernet

        return Fernet(self._ensure_key())

    # -- TokenStorage interface ----------------------------------------------

    def save_token(self, token: str) -> None:
        encrypted = self._fernet().encrypt(token.encode())
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._token_path.write_bytes(encrypted)
        os.chmod(self._token_path, 0o600)

    def load_token(self) -> str | None:
        if not self._token_path.exists():
            return None
        try:
            return self._fernet().decrypt(self._token_path.read_bytes()).decode()
        except Exception:  # noqa: BLE001
            return None

    def delete_token(self) -> bool:
        if not self._token_path.exists():
            return False
        self._token_path.unlink()
        return True


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_storage() -> TokenStorage:
    """Return the best available :class:`TokenStorage`.

    Tries :class:`KeyringStorage` first; falls back to :class:`FileStorage`
    when the system keyring is unavailable.
    """
    try:
        import keyring
        from keyring.backends.fail import Keyring as FailKeyring

        backend = keyring.get_keyring()
        if isinstance(backend, FailKeyring):
            raise RuntimeError("keyring backend is FailKeyring")

        # Smoke-test: ensure we can actually talk to the backend.
        keyring.get_password(SERVICE_NAME, "__probe__")
        return KeyringStorage()
    except Exception:  # noqa: BLE001
        _console.print(
            "[yellow]⚠ System keyring unavailable – "
            "falling back to encrypted file storage.[/yellow]"
        )
        return FileStorage()
