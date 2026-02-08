from __future__ import annotations

from pathlib import Path

from gh_agent_funhouse import config


def test_get_config_dir_returns_path():
    result = config.get_config_dir()
    assert isinstance(result, Path)


def test_get_data_dir_returns_path():
    result = config.get_data_dir()
    assert isinstance(result, Path)


def test_set_and_get_current_repo(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "get_config_dir", lambda: tmp_path)
    monkeypatch.setattr(config, "get_config_path", lambda: tmp_path / "config.json")

    config.set_current_repo("octocat/Hello-World")
    assert config.get_current_repo() == "octocat/Hello-World"


def test_get_current_repo_returns_none_when_not_set(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "get_config_dir", lambda: tmp_path)
    monkeypatch.setattr(config, "get_config_path", lambda: tmp_path / "config.json")

    assert config.get_current_repo() is None
