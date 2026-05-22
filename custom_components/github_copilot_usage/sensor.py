"""Sensor platform for GitHub Copilot Usage."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import GitHubCopilotUsageCoordinator
from .entity import GitHubCopilotUsageEntity


@dataclass(frozen=True, kw_only=True)
class GitHubCopilotQuotaSensorDescription(SensorEntityDescription):
    """Describe a GitHub Copilot quota sensor."""

    quota_key: str


DEFAULT_ICONS = {
    "chat": "mdi:message-badge-outline",
    "completions": "mdi:code-braces",
    "premium_interactions": "mdi:robot-love-outline",
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up GitHub Copilot Usage sensors from a config entry."""
    coordinator: GitHubCopilotUsageCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        "coordinator"
    ]
    known_entities: set[str] = set()

    @callback
    def async_add_missing_entities() -> None:
        current_unique_ids: set[str] = set()
        new_entities: list[GitHubCopilotQuotaSensor] = []

        snapshots = coordinator.data.get("quota_snapshots")
        if not isinstance(snapshots, dict):
            return

        for quota_key in snapshots:
            unique_id = f"{config_entry.entry_id}_{quota_key}"
            current_unique_ids.add(unique_id)
            if unique_id in known_entities:
                continue

            known_entities.add(unique_id)
            new_entities.append(
                GitHubCopilotQuotaSensor(
                    coordinator=coordinator,
                    description=_build_description(quota_key),
                    unique_id=unique_id,
                )
            )

        known_entities.clear()
        known_entities.update(current_unique_ids)

        if new_entities:
            async_add_entities(new_entities)

    async_add_missing_entities()
    config_entry.async_on_unload(
        coordinator.async_add_listener(async_add_missing_entities)
    )


def _build_description(quota_key: str) -> GitHubCopilotQuotaSensorDescription:
    """Build a sensor description for one quota key."""
    title = quota_key.replace("_", " ").title()
    return GitHubCopilotQuotaSensorDescription(
        key=quota_key,
        quota_key=quota_key,
        name=f"{title} Remaining",
        icon=DEFAULT_ICONS.get(quota_key, "mdi:counter"),
    )


class GitHubCopilotQuotaSensor(GitHubCopilotUsageEntity, SensorEntity):
    """Sensor for one GitHub Copilot quota bucket."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = "requests"

    def __init__(
        self,
        coordinator: GitHubCopilotUsageCoordinator,
        description: GitHubCopilotQuotaSensorDescription,
        unique_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = unique_id

    @property
    def available(self) -> bool:
        """Return whether data for this quota bucket is available."""
        return (
            self.coordinator.last_update_success
            and self._quota_snapshot is not None
        )

    @property
    def native_value(self) -> int | None:
        """Return the remaining quota."""
        snapshot = self._quota_snapshot
        if snapshot is None:
            return None
        if snapshot.get("unlimited") is True:
            return None

        remaining = snapshot.get("remaining")
        if isinstance(remaining, int):
            return remaining
        if isinstance(remaining, float):
            return int(remaining)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes for the quota bucket."""
        snapshot = self._quota_snapshot
        payload = self.coordinator.data
        if snapshot is None:
            return {}

        attributes = dict(snapshot)
        if isinstance(attributes.get("timestamp_utc"), str):
            try:
                attributes["timestamp_utc"] = datetime.fromisoformat(
                    attributes["timestamp_utc"].replace("Z", "+00:00")
                ).isoformat()
            except ValueError:
                pass
        attributes["copilot_plan"] = payload.get("copilot_plan")
        attributes["access_type_sku"] = payload.get("access_type_sku")
        attributes["quota_reset_date"] = payload.get("quota_reset_date")
        attributes["quota_reset_date_utc"] = payload.get("quota_reset_date_utc")
        return attributes

    @property
    def _quota_snapshot(self) -> dict[str, Any] | None:
        """Return the snapshot for this sensor."""
        snapshots = self.coordinator.data.get("quota_snapshots")
        if not isinstance(snapshots, dict):
            return None

        snapshot = snapshots.get(self.entity_description.quota_key)
        if isinstance(snapshot, dict):
            return snapshot
        return None
