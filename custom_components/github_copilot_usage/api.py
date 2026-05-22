"""API client for GitHub Copilot Usage."""

from __future__ import annotations

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

        return payload
