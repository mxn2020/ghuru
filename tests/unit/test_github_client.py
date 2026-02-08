from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from gh_agent_funhouse.github_client import GitHubClient, _redact_token


def _make_client(token: str = "ghp_test_token_abc123") -> GitHubClient:
    return GitHubClient(token=token)


def _mock_response(
    status_code: int = 200,
    json_data: object = None,
    text: str = "",
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.text = text or ""
    resp.headers = headers or {}
    return resp


class TestGitHubClientInit:
    def test_initialization_stores_token(self):
        client = _make_client("ghp_mytoken")
        assert client._token == "ghp_mytoken"

    def test_initialization_creates_httpx_client(self):
        client = _make_client()
        assert isinstance(client._client, httpx.Client)
        client.close()


class TestGetUser:
    def test_get_user_returns_data(self):
        client = _make_client()
        user_data = {"login": "octocat", "id": 1}
        mock_resp = _mock_response(json_data=user_data)

        with patch.object(client._client, "request", return_value=mock_resp):
            result = client.get_user()

        assert result == user_data


class TestListRepos:
    def test_list_repos_returns_list(self):
        client = _make_client()
        repos = [{"name": "repo1"}, {"name": "repo2"}]
        mock_resp = _mock_response(json_data=repos)

        with patch.object(client._client, "request", return_value=mock_resp):
            result = client.list_repos()

        assert result == repos


class TestCreateRepo:
    def test_create_repo_sends_correct_payload(self):
        client = _make_client()
        created = {"name": "new-repo", "private": True}
        mock_resp = _mock_response(json_data=created)

        with patch.object(client._client, "request", return_value=mock_resp) as mock_req:
            result = client.create_repo("new-repo", private=True)

        assert result == created
        call_kwargs = mock_req.call_args
        assert call_kwargs[0][0] == "POST"
        assert call_kwargs[0][1] == "/user/repos"
        assert call_kwargs[1]["json"]["name"] == "new-repo"
        assert call_kwargs[1]["json"]["private"] is True


class TestRateLimitHandling:
    def test_rate_limit_raises_after_retries(self):
        client = _make_client()
        mock_resp = _mock_response(
            status_code=403,
            text="API rate limit exceeded",
            headers={"X-RateLimit-Reset": "0"},
        )

        with patch.object(client._client, "request", return_value=mock_resp), \
             patch("gh_agent_funhouse.github_client.time.sleep"):
            with pytest.raises(RuntimeError, match="rate limit"):
                client.get("/user")


class TestTokenRedaction:
    def test_redact_token_replaces_token(self):
        token = "ghp_secret123"
        text = f"Error connecting with token {token} to server"
        redacted = _redact_token(text, token)
        assert token not in redacted
        assert "***" in redacted

    def test_token_not_in_http_error_message(self):
        token = "ghp_supersecret"
        client = GitHubClient(token=token)

        with patch.object(
            client._client, "request",
            side_effect=httpx.ConnectError(f"Failed to connect with {token}"),
        ):
            with pytest.raises(RuntimeError) as exc_info:
                client.get("/user")
            assert token not in str(exc_info.value)

    def test_token_not_in_api_error_body(self):
        token = "ghp_leaked"
        client = GitHubClient(token=token)
        mock_resp = _mock_response(
            status_code=422,
            text=f"Validation failed for token {token}",
        )

        with patch.object(client._client, "request", return_value=mock_resp):
            with pytest.raises(RuntimeError) as exc_info:
                client.get("/user")
            assert token not in str(exc_info.value)
