"""Coordinator for GitHub Copilot Usage."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import GitHubCopilotUsageApiClient
from .const import DOMAIN
from .exceptions import (
    GitHubCopilotUsageApiError,
    GitHubCopilotUsageAuthenticationError,
)

_LOGGER = logging.getLogger(__name__)


class GitHubCopilotUsageCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate GitHub Copilot Usage API updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: GitHubCopilotUsageApiClient,
        update_interval_seconds: int,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval_seconds),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from GitHub."""
        try:
            return await self.client.async_fetch_user()
        except GitHubCopilotUsageAuthenticationError as err:
            raise ConfigEntryAuthFailed from err
        except GitHubCopilotUsageApiError as err:
            raise UpdateFailed(str(err)) from err
