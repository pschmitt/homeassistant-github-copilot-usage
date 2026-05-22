"""Config flow for GitHub Copilot Usage."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_NAME, CONF_SCAN_INTERVAL, CONF_TOKEN
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import GitHubCopilotUsageApiClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, MIN_SCAN_INTERVAL
from .exceptions import (
    GitHubCopilotUsageApiError,
    GitHubCopilotUsageAuthenticationError,
)

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass, data: dict[str, Any]) -> dict[str, str]:
    """Validate the config flow input."""
    session = async_create_clientsession(hass)
    client = GitHubCopilotUsageApiClient(
        session=session,
        token=data[CONF_TOKEN],
    )
    payload = await client.async_validate()
    login = payload.get("login")
    title = data.get(CONF_NAME) or (
        f"GitHub Copilot ({login})" if isinstance(login, str) and login else "GitHub Copilot"
    )

    return {
        "title": title,
        "unique_id": login if isinstance(login, str) and login else title,
    }


class GitHubCopilotUsageConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for GitHub Copilot Usage."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> GitHubCopilotUsageOptionsFlow:
        """Return the options flow."""
        return GitHubCopilotUsageOptionsFlow(config_entry)

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the user step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except GitHubCopilotUsageAuthenticationError:
                errors["base"] = "invalid_auth"
            except GitHubCopilotUsageApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception(
                    "Unexpected exception while validating GitHub Copilot Usage config"
                )
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(info["unique_id"])
                self._abort_if_unique_id_configured()
                data = {
                    CONF_TOKEN: user_input[CONF_TOKEN],
                }
                options = {
                    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                }
                return self.async_create_entry(title=info["title"], data=data, options=options)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_NAME): TextSelector(),
                    vol.Required(CONF_TOKEN): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                }
            ),
            errors=errors,
        )


class GitHubCopilotUsageOptionsFlow(OptionsFlow):
    """Handle options for GitHub Copilot Usage."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Manage general integration options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self._config_entry.options.get(
                            CONF_SCAN_INTERVAL,
                            DEFAULT_SCAN_INTERVAL,
                        ),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL,
                            mode=NumberSelectorMode.BOX,
                            step=60,
                        )
                    ),
                }
            ),
        )
