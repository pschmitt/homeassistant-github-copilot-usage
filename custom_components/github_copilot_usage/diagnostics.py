"""Diagnostics support for GitHub Copilot Usage."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

TO_REDACT = {"token"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    entry = hass.data[DOMAIN][config_entry.entry_id]
    return {
        "config_entry": async_redact_data(dict(config_entry.data), TO_REDACT),
        "options": dict(config_entry.options),
        "data": entry["coordinator"].data,
    }
