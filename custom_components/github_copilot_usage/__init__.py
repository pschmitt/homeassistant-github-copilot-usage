"""The GitHub Copilot Usage integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import GitHubCopilotUsageApiClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, PLATFORMS
from .coordinator import GitHubCopilotUsageCoordinator

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the GitHub Copilot Usage integration."""
    del config
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up GitHub Copilot Usage from a config entry."""
    session = async_get_clientsession(hass)
    client = GitHubCopilotUsageApiClient(
        session=session,
        token=config_entry.data[CONF_TOKEN],
    )
    coordinator = GitHubCopilotUsageCoordinator(
        hass=hass,
        config_entry=config_entry,
        client=client,
        update_interval_seconds=config_entry.options.get(
            CONF_SCAN_INTERVAL,
            DEFAULT_SCAN_INTERVAL,
        ),
    )

    hass.data[DOMAIN][config_entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }

    if coordinator.data is None:
        coordinator.last_update_success = False
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    config_entry.async_on_unload(config_entry.add_update_listener(async_update_listener))
    config_entry.async_create_background_task(
        hass, coordinator.async_refresh(), "github_copilot_usage_first_refresh"
    )
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a GitHub Copilot Usage config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)
    return unload_ok


async def async_update_listener(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Reload the integration after options changes."""
    await hass.config_entries.async_reload(config_entry.entry_id)
