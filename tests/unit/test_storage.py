from __future__ import annotations

from unittest.mock import MagicMock, patch

from gh_agent_funhouse.auth.storage import FileStorage, TokenStorage, get_storage


def test_file_storage_save_load_roundtrip(tmp_path):
    storage = FileStorage(config_dir=tmp_path)
    storage.save_token("ghp_test_token_12345")
    loaded = storage.load_token()
    assert loaded == "ghp_test_token_12345"


def test_file_storage_delete_roundtrip(tmp_path):
    storage = FileStorage(config_dir=tmp_path)
    storage.save_token("ghp_deleteme")
    assert storage.delete_token() is True
    assert storage.load_token() is None


def test_file_storage_load_returns_none_when_empty(tmp_path):
    storage = FileStorage(config_dir=tmp_path)
    assert storage.load_token() is None


def test_file_storage_delete_returns_false_when_no_token(tmp_path):
    storage = FileStorage(config_dir=tmp_path)
    assert storage.delete_token() is False


def test_get_storage_returns_file_storage_when_keyring_unavailable():
    mock_keyring = MagicMock()
    mock_keyring.get_keyring.side_effect = RuntimeError("no keyring")
    with patch.dict("sys.modules", {"keyring": mock_keyring, "keyring.backends.fail": MagicMock()}):
        result = get_storage()
    assert isinstance(result, FileStorage)
    assert isinstance(result, TokenStorage)
