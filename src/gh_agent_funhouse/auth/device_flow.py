"""GitHub Device Flow OAuth implementation for gh-agent-funhouse.

Implements the device authorization grant flow described at
https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps#device-flow
"""

from __future__ import annotations

import time

import httpx
from rich.console import Console
from rich.panel import Panel

_console = Console()

_DEVICE_CODE_URL = "https://github.com/login/device/code"
_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"


class DeviceFlowError(Exception):
    """Raised when the device flow cannot be completed."""


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def start_device_flow(client_id: str) -> dict[str, str | int]:
    """Initiate the GitHub device flow and return the response payload.

    Returns a dict with at least ``device_code``, ``user_code``,
    ``verification_uri``, ``expires_in``, and ``interval``.
    """
    with httpx.Client() as client:
        resp = client.post(
            _DEVICE_CODE_URL,
            data={"client_id": client_id, "scope": "repo user"},
            headers={"Accept": "application/json"},
        )

    if resp.status_code != 200:
        raise DeviceFlowError(
            f"Failed to start device flow (HTTP {resp.status_code}): {resp.text}"
        )

    data: dict[str, str | int] = resp.json()
    required = {"device_code", "user_code", "verification_uri"}
    missing = required - data.keys()
    if missing:
        raise DeviceFlowError(f"Incomplete device-flow response – missing: {missing}")

    return data


def poll_for_token(client_id: str, device_code: str, interval: int = 5) -> str:
    """Poll GitHub until the user authorises the device or the code expires.

    Parameters
    ----------
    client_id:
        The OAuth application's client ID.
    device_code:
        The ``device_code`` returned by :func:`start_device_flow`.
    interval:
        Minimum seconds between poll requests.

    Returns
    -------
    str
        The OAuth access token.
    """
    wait = interval

    with httpx.Client() as client:
        while True:
            time.sleep(wait)
            resp = client.post(
                _ACCESS_TOKEN_URL,
                data={
                    "client_id": client_id,
                    "device_code": device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
                headers={"Accept": "application/json"},
            )

            body: dict[str, str] = resp.json()

            if "access_token" in body:
                return body["access_token"]

            error = body.get("error", "")

            if error == "authorization_pending":
                continue

            if error == "slow_down":
                # GitHub asks us to add 5 s to the interval.
                wait += 5
                continue

            if error == "expired_token":
                raise DeviceFlowError(
                    "Device code expired.  Please restart the login flow."
                )

            if error == "access_denied":
                raise DeviceFlowError("Authorization was denied by the user.")

            raise DeviceFlowError(
                f"Unexpected device-flow error: {error} – "
                f"{body.get('error_description', '')}"
            )


# ---------------------------------------------------------------------------
# High-level convenience
# ---------------------------------------------------------------------------


def run_device_flow(client_id: str) -> str:
    """Run the full device-flow interactively and return the access token."""
    flow = start_device_flow(client_id)

    user_code = flow["user_code"]
    verification_uri = flow["verification_uri"]
    device_code = str(flow["device_code"])
    interval = int(flow.get("interval", 5))

    _console.print(
        Panel(
            f"[bold]Open [cyan]{verification_uri}[/cyan] in your browser\n"
            f"and enter code: [green]{user_code}[/green][/bold]",
            title="GitHub Device Authorisation",
            border_style="bright_blue",
        )
    )

    with _console.status("[bold cyan]Waiting for authorisation…[/bold cyan]"):
        token = poll_for_token(client_id, device_code, interval)

    _console.print("[green]✓ Device authorisation complete.[/green]")
    return token
