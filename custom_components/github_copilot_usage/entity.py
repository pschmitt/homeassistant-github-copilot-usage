"""Entity helpers for GitHub Copilot Usage."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import GitHubCopilotUsageCoordinator


class GitHubCopilotUsageEntity(CoordinatorEntity[GitHubCopilotUsageCoordinator]):
    """Base entity for GitHub Copilot Usage."""

    _attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for the integration device."""
        payload = self.coordinator.data
        login = payload.get("login", "github")
        return DeviceInfo(
            identifiers={(DOMAIN, str(login))},
            name=f"GitHub Copilot ({login})",
            manufacturer="GitHub",
            model=payload.get("copilot_plan", "Copilot"),
        )
