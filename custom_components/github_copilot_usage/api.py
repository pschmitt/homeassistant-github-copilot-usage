"""API client for GitHub Copilot Usage."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import aiohttp
from aiogithubapi import (
    GitHubAPI,
    GitHubAuthenticationException,
    GitHubConnectionException,
    GitHubException,
)

from .exceptions import (
    GitHubCopilotUsageApiError,
    GitHubCopilotUsageAuthenticationError,
)


def _subtract_one_month(dt: datetime) -> datetime:
    """Return dt shifted back exactly one calendar month, clamping day overflow."""
    year, month = dt.year, dt.month - 1
    if month < 1:
        month, year = 12, year - 1
    # Clamp to the shifted month's last day (e.g. Mar 31 -> Feb 28/29).
    day = min(dt.day, _days_in_month(year, month))
    return dt.replace(year=year, month=month, day=day)


def _days_in_month(year: int, month: int) -> int:
    """Return the number of days in year/month without pulling in calendar/dateutil."""
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1
    return (datetime(next_year, next_month, 1) - datetime(year, month, 1)).days


def _quota_period_percent_elapsed(reset_date_utc: str | None) -> float | None:
    """Estimate how far "now" is through the current monthly quota period.

    Copilot's quota resets on a monthly cycle anchored to
    ``quota_reset_date_utc``, but the payload carries no explicit
    period-start, so the previous reset is approximated as exactly one
    calendar month before the next one.
    """
    if not reset_date_utc:
        return None
    try:
        reset_dt = datetime.fromisoformat(reset_date_utc.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if reset_dt.tzinfo is None:
        reset_dt = reset_dt.replace(tzinfo=UTC)

    period_start = _subtract_one_month(reset_dt)
    period_seconds = (reset_dt - period_start).total_seconds()
    if period_seconds <= 0:
        return None

    elapsed_seconds = (datetime.now(UTC) - period_start).total_seconds()
    return max(0.0, min(100.0, (elapsed_seconds / period_seconds) * 100))


class GitHubCopilotUsageApiClient:
    """Client for the GitHub Copilot usage endpoint."""

    def __init__(self, session: aiohttp.ClientSession, token: str) -> None:
        """Initialize the client."""
        self._api = GitHubAPI(
            token=token,
            session=session,
            api_version="2022-11-28",
        )

    async def async_validate(self) -> dict[str, Any]:
        """Validate the configured token and return the payload."""
        return await self.async_fetch_user()

    async def async_fetch_user(self) -> dict[str, Any]:
        """Fetch the GitHub Copilot usage payload."""
        try:
            response = await self._api.generic("/copilot_internal/user")
            payload = response.data
        except GitHubAuthenticationException as err:
            raise GitHubCopilotUsageAuthenticationError from err
        except GitHubConnectionException as err:
            raise GitHubCopilotUsageApiError("GitHub API request failed") from err
        except GitHubException as err:
            raise GitHubCopilotUsageApiError(f"GitHub API error: {err}") from err

        if not isinstance(payload, dict):
            raise GitHubCopilotUsageApiError("Unexpected GitHub API payload")

        quota_snapshots = payload.get("quota_snapshots")
        if not isinstance(quota_snapshots, dict):
            raise GitHubCopilotUsageApiError("Missing quota_snapshots in payload")

        percent_elapsed = _quota_period_percent_elapsed(payload.get("quota_reset_date_utc"))
        if percent_elapsed is not None:
            payload["quota_period_percent_elapsed"] = round(percent_elapsed, 1)

        return payload
