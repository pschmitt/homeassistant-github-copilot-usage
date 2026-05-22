"""Sensor platform for GitHub Copilot Usage."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import GitHubCopilotUsageCoordinator
from .entity import GitHubCopilotUsageEntity


@dataclass(frozen=True, kw_only=True)
class GitHubCopilotQuotaSensorDescription(SensorEntityDescription):
    """Describe a GitHub Copilot quota sensor."""

    quota_key: str
    metric: str


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
        new_entities: list[SensorEntity] = []

        reset_unique_id = f"{config_entry.entry_id}_quota_reset"
        current_unique_ids.add(reset_unique_id)
        if reset_unique_id not in known_entities:
            known_entities.add(reset_unique_id)
            new_entities.append(
                GitHubCopilotResetSensor(
                    coordinator=coordinator,
                    unique_id=reset_unique_id,
                )
            )

        snapshots = coordinator.data.get("quota_snapshots")
        if isinstance(snapshots, dict):
            for quota_key in snapshots:
                for description in _build_descriptions(quota_key):
                    unique_id = f"{config_entry.entry_id}_{quota_key}_{description.metric}"
                    current_unique_ids.add(unique_id)
                    if unique_id in known_entities:
                        continue

                    known_entities.add(unique_id)
                    new_entities.append(
                        GitHubCopilotQuotaSensor(
                            coordinator=coordinator,
                            description=description,
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


def _build_descriptions(
    quota_key: str,
) -> tuple[GitHubCopilotQuotaSensorDescription, ...]:
    """Build sensor descriptions for one quota key."""
    title = quota_key.replace("_", " ").title()
    icon = DEFAULT_ICONS.get(quota_key, "mdi:counter")
    return (
        GitHubCopilotQuotaSensorDescription(
            key=f"{quota_key}_remaining",
            quota_key=quota_key,
            metric="remaining",
            name=f"{title} Remaining",
            icon=icon,
        ),
        GitHubCopilotQuotaSensorDescription(
            key=f"{quota_key}_entitlement",
            quota_key=quota_key,
            metric="entitlement",
            name=f"{title} Entitlement",
            icon="mdi:counter",
        ),
        GitHubCopilotQuotaSensorDescription(
            key=f"{quota_key}_percent_used",
            quota_key=quota_key,
            metric="percent_used",
            name=f"{title} Used",
            icon="mdi:percent",
        ),
    )


class GitHubCopilotResetSensor(GitHubCopilotUsageEntity, SensorEntity):
    """Sensor for the global Copilot quota reset time."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self,
        coordinator: GitHubCopilotUsageCoordinator,
        unique_id: str,
    ) -> None:
        """Initialize the reset-time sensor."""
        super().__init__(coordinator)
        self._attr_name = "Quota Reset"
        self._attr_unique_id = unique_id
        self._attr_icon = "mdi:calendar-refresh"

    @property
    def native_value(self) -> datetime | None:
        """Return the global quota reset timestamp."""
        value = self.coordinator.data.get("quota_reset_date_utc")
        if not isinstance(value, str):
            return None
        return _parse_datetime(value)


class GitHubCopilotQuotaSensor(GitHubCopilotUsageEntity, SensorEntity):
    """Sensor for one GitHub Copilot quota bucket metric."""

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
        return self.coordinator.last_update_success and self._quota_snapshot is not None

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the native unit for the current metric."""
        if self.entity_description.metric == "percent_used":
            return "%"
        if self.entity_description.metric == "remaining":
            if self._quota_snapshot and self._quota_snapshot.get("unlimited") is True:
                return None
            return "requests"
        return "requests"

    @property
    def native_value(self) -> str | int | float | None:
        """Return the metric value."""
        snapshot = self._quota_snapshot
        if snapshot is None:
            return None

        if self.entity_description.metric == "remaining":
            if snapshot.get("unlimited") is True:
                return "Unlimited"
            return _coerce_number(snapshot.get("remaining"))

        if self.entity_description.metric == "entitlement":
            if snapshot.get("unlimited") is True:
                return "Unlimited"
            return _coerce_number(snapshot.get("entitlement"))

        if self.entity_description.metric == "percent_used":
            percent_remaining = snapshot.get("percent_remaining")
            if not isinstance(percent_remaining, (int, float)):
                return None
            return round(100 - float(percent_remaining), 1)

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
            parsed = _parse_datetime(attributes["timestamp_utc"])
            if parsed is not None:
                attributes["timestamp_utc"] = parsed.isoformat()
        attributes["percent_used"] = self._percent_used(snapshot)
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

    @staticmethod
    def _percent_used(snapshot: dict[str, Any]) -> float | None:
        """Return the percent used for one snapshot."""
        percent_remaining = snapshot.get("percent_remaining")
        if not isinstance(percent_remaining, (int, float)):
            return None
        return round(100 - float(percent_remaining), 1)


def _coerce_number(value: Any) -> int | float | None:
    """Return an int or float from a GitHub payload value."""
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return round(value, 1)
    return None


def _parse_datetime(value: str) -> datetime | None:
    """Parse one ISO timestamp into a Home Assistant-aware datetime."""
    try:
        return dt_util.parse_datetime(value)
    except (TypeError, ValueError):
        return None
