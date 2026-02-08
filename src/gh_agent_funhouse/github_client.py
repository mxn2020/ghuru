"""GitHub REST API client for gh-agent-funhouse.

Wraps :mod:`httpx` with authentication, rate-limit handling, token
redaction, and convenience methods for common GitHub operations.
"""

from __future__ import annotations

import re
import time
from typing import Any

import httpx

BASE_URL = "https://api.github.com"
USER_AGENT = "gh-agent-funhouse"
_MAX_RETRIES = 3
_DEFAULT_BACKOFF = 1.0  # seconds


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------


def _get_stored_token() -> str:
    """Retrieve the GitHub token from *keyring* auth storage."""
    import keyring  # lazy import to keep module lightweight

    token: str | None = keyring.get_password("gh-agent-funhouse", "github-token")
    if not token:
        raise RuntimeError("No GitHub token found.  Run `ghfun auth login` to authenticate.")
    return token


def _redact_token(text: str, token: str) -> str:
    """Replace any occurrence of *token* in *text* with ``***``."""
    return text.replace(token, "***") if token else text


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class GitHubClient:
    """Thin wrapper around :class:`httpx.Client` for the GitHub REST API."""

    def __init__(self, token: str) -> None:
        self._token = token
        self._client = httpx.Client(
            base_url=BASE_URL,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "User-Agent": USER_AGENT,
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )

    # -- low-level verbs -----------------------------------------------------

    def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Execute a request with rate-limit back-off and token redaction."""
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = self._client.request(method, url, **kwargs)
            except httpx.HTTPError as exc:
                raise RuntimeError(_redact_token(str(exc), self._token)) from None

            if response.status_code == 403 and "rate limit" in response.text.lower():
                reset = response.headers.get("X-RateLimit-Reset")
                wait = (
                    max(int(reset) - int(time.time()), 0) + 1
                    if reset
                    else _DEFAULT_BACKOFF * attempt
                )
                if attempt < _MAX_RETRIES:
                    time.sleep(wait)
                    continue
                raise RuntimeError(f"GitHub API rate limit exceeded.  Resets at epoch {reset}.")

            if response.status_code == 401:
                raise RuntimeError(
                    "GitHub authentication failed – check your token (run `ghfun auth login`)."
                )

            if response.status_code >= 400:
                body = _redact_token(response.text, self._token)
                raise RuntimeError(
                    f"GitHub API error {response.status_code} {method.upper()} {url}: {body}"
                )
            return response

        # Should be unreachable, but keeps mypy happy.
        raise RuntimeError("Unexpected retry exhaustion")  # pragma: no cover

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        """Send a GET request."""
        return self._request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        """Send a POST request."""
        return self._request("POST", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> httpx.Response:
        """Send a PUT request."""
        return self._request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        """Send a DELETE request."""
        return self._request("DELETE", url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> httpx.Response:
        """Send a PATCH request."""
        return self._request("PATCH", url, **kwargs)

    def close(self) -> None:
        """Close the underlying HTTP transport."""
        self._client.close()

    # -- convenience methods -------------------------------------------------

    def get_user(self) -> dict[str, Any]:
        """Return the authenticated user's profile."""
        return self.get("/user").json()  # type: ignore[no-any-return]

    def list_repos(
        self,
        per_page: int = 30,
        page: int = 1,
        sort: str = "updated",
    ) -> list[dict[str, Any]]:
        """List repositories for the authenticated user."""
        return self.get(  # type: ignore[no-any-return]
            "/user/repos",
            params={"per_page": per_page, "page": page, "sort": sort},
        ).json()

    def get_repo(self, owner: str, repo: str) -> dict[str, Any]:
        """Get a single repository."""
        return self.get(f"/repos/{owner}/{repo}").json()  # type: ignore[no-any-return]

    def create_repo(self, name: str, *, private: bool = True, **kwargs: Any) -> dict[str, Any]:
        """Create a new repository for the authenticated user."""
        payload: dict[str, Any] = {"name": name, "private": private, **kwargs}
        return self.post("/user/repos", json=payload).json()  # type: ignore[no-any-return]

    # -- issues --------------------------------------------------------------

    def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        *,
        body: str = "",
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create an issue in *owner/repo*."""
        payload: dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        return self.post(  # type: ignore[no-any-return]
            f"/repos/{owner}/{repo}/issues", json=payload
        ).json()

    def list_issues(
        self,
        owner: str,
        repo: str,
        *,
        state: str = "open",
        per_page: int = 30,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        """List issues for *owner/repo*."""
        return self.get(  # type: ignore[no-any-return]
            f"/repos/{owner}/{repo}/issues",
            params={"state": state, "per_page": per_page, "page": page},
        ).json()

    def get_issue(self, owner: str, repo: str, number: int) -> dict[str, Any]:
        """Get a single issue by number."""
        return self.get(  # type: ignore[no-any-return]
            f"/repos/{owner}/{repo}/issues/{number}"
        ).json()

    # -- labels --------------------------------------------------------------

    def create_label(
        self,
        owner: str,
        repo: str,
        name: str,
        *,
        color: str = "ededed",
        description: str = "",
    ) -> dict[str, Any]:
        """Create a label in *owner/repo*."""
        payload: dict[str, Any] = {
            "name": name,
            "color": re.sub(r"^#", "", color),
            "description": description,
        }
        return self.post(  # type: ignore[no-any-return]
            f"/repos/{owner}/{repo}/labels", json=payload
        ).json()

    # -- pull requests -------------------------------------------------------

    def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str,
        *,
        body: str = "",
    ) -> dict[str, Any]:
        """Create a pull request in *owner/repo*."""
        payload: dict[str, Any] = {
            "title": title,
            "head": head,
            "base": base,
            "body": body,
        }
        return self.post(  # type: ignore[no-any-return]
            f"/repos/{owner}/{repo}/pulls", json=payload
        ).json()

    # -- actions / workflows -------------------------------------------------

    def dispatch_workflow(
        self,
        owner: str,
        repo: str,
        workflow_id: str | int,
        ref: str = "main",
        inputs: dict[str, str] | None = None,
    ) -> None:
        """Trigger a workflow_dispatch event."""
        payload: dict[str, Any] = {"ref": ref}
        if inputs:
            payload["inputs"] = inputs
        self.post(
            f"/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches",
            json=payload,
        )

    def get_workflow_runs(
        self,
        owner: str,
        repo: str,
        *,
        per_page: int = 10,
        page: int = 1,
    ) -> dict[str, Any]:
        """List workflow runs for *owner/repo*."""
        return self.get(  # type: ignore[no-any-return]
            f"/repos/{owner}/{repo}/actions/runs",
            params={"per_page": per_page, "page": page},
        ).json()

    def get_workflow_run(self, owner: str, repo: str, run_id: int) -> dict[str, Any]:
        """Get a single workflow run."""
        return self.get(  # type: ignore[no-any-return]
            f"/repos/{owner}/{repo}/actions/runs/{run_id}"
        ).json()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_client() -> GitHubClient:
    """Create a :class:`GitHubClient` using the token from auth storage."""
    return GitHubClient(_get_stored_token())
