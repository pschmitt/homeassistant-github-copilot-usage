"""Config flow for GitHub Copilot Usage."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from aiogithubapi import GitHubDeviceAPI, GitHubException
from aiogithubapi.const import OAUTH_USER_LOGIN
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_NAME, CONF_SCAN_INTERVAL, CONF_TOKEN
from homeassistant.core import HomeAssistant, callback
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
from .const import (
    AUTH_METHOD_DEVICE,
    AUTH_METHOD_PAT,
    CONF_AUTH_METHOD,
    CONF_CLIENT_ID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)
from .exceptions import (
    GitHubCopilotUsageApiError,
    GitHubCopilotUsageAuthenticationError,
)

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, str]:
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
    login_task: asyncio.Task | None = None

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._user_input: dict[str, Any] = {}
        self._device: GitHubDeviceAPI | None = None
        self._device_login = None
        self._oauth_login = None

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
        del user_input
        return self.async_show_menu(
            step_id="user",
            menu_options=["personal_access_token", "device_flow"],
        )

    async def async_step_personal_access_token(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the PAT auth step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(
                    self.hass,
                    {
                        CONF_TOKEN: user_input[CONF_TOKEN],
                    },
                )
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
                    CONF_AUTH_METHOD: AUTH_METHOD_PAT,
                    CONF_TOKEN: user_input[CONF_TOKEN],
                }
                options = {
                    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                }
                title = user_input.get(CONF_NAME) or info["title"]
                return self.async_create_entry(title=title, data=data, options=options)

        return self.async_show_form(
            step_id="personal_access_token",
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

    async def async_step_device_flow(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Start GitHub device flow."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._user_input = dict(user_input)
            session = async_create_clientsession(self.hass)
            self._device = GitHubDeviceAPI(
                client_id=user_input[CONF_CLIENT_ID],
                session=session,
            )

            try:
                response = await self._device.register()
                self._device_login = response.data
            except GitHubException:
                _LOGGER.exception("Unable to register GitHub device flow")
                errors["base"] = "could_not_register"
            else:
                if self.login_task is None:
                    self.login_task = self.hass.async_create_task(
                        self._async_wait_for_device_login()
                    )
                return await self.async_step_device_flow_progress()

        return self.async_show_form(
            step_id="device_flow",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_NAME): TextSelector(),
                    vol.Required(CONF_CLIENT_ID): TextSelector(),
                }
            ),
            errors=errors,
        )

    async def _async_wait_for_device_login(self) -> None:
        """Wait for GitHub device flow activation to complete."""
        if self._device is None or self._device_login is None:
            return

        response = await self._device.activation(
            device_code=self._device_login.device_code
        )
        self._oauth_login = response.data

    async def async_step_device_flow_progress(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Show progress for GitHub device flow."""
        del user_input
        if self.login_task is None or self._device_login is None:
            return self.async_abort(reason="could_not_register")

        if self.login_task.done():
            if self.login_task.exception():
                return self.async_show_progress_done(next_step_id="could_not_register")
            return self.async_show_progress_done(next_step_id="device_flow_done")

        return self.async_show_progress(
            step_id="device_flow_progress",
            progress_action="wait_for_device",
            description_placeholders={
                "url": OAUTH_USER_LOGIN,
                "code": self._device_login.user_code or "",
            },
            progress_task=self.login_task,
        )

    async def async_step_device_flow_done(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Finish device flow and create the entry."""
        del user_input
        if self._oauth_login is None or not self._oauth_login.access_token:
            return self.async_abort(reason="invalid_auth")

        try:
            info = await validate_input(
                self.hass,
                {
                    CONF_TOKEN: self._oauth_login.access_token,
                },
            )
        except GitHubCopilotUsageAuthenticationError:
            return self.async_abort(reason="oauth_not_supported")
        except GitHubCopilotUsageApiError:
            return self.async_abort(reason="cannot_connect")
        except Exception:  # noqa: BLE001
            _LOGGER.exception(
                "Unexpected exception while validating GitHub Copilot Usage device flow"
            )
            return self.async_abort(reason="unknown")

        await self.async_set_unique_id(info["unique_id"])
        self._abort_if_unique_id_configured()
        data = {
            CONF_AUTH_METHOD: AUTH_METHOD_DEVICE,
            CONF_CLIENT_ID: self._user_input[CONF_CLIENT_ID],
            CONF_TOKEN: self._oauth_login.access_token,
        }
        options = {
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
        }
        title = self._user_input.get(CONF_NAME) or info["title"]
        return self.async_create_entry(title=title, data=data, options=options)

    async def async_step_could_not_register(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle device-flow registration failures."""
        del user_input
        return self.async_abort(reason="could_not_register")


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
